#!/usr/bin/env python3
"""Generate a short Mandarin line from an immutable course voice reference."""

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time
import wave
import os
import tempfile
from contextlib import contextmanager


DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "assets/voice-catalog.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_catalog(path):
    catalog = json.loads(path.read_text(encoding="utf-8"))
    voices = catalog["voices"] + catalog.get("comparison_references", [])
    if len({voice["id"] for voice in voices}) != len(voices):
        raise ValueError("音色编号重复")
    return catalog, {voice["id"]: voice for voice in voices}


def reference_for(catalog_path, catalog, voice):
    root = catalog_path.parent.resolve()
    reference = (root / voice["reference_audio"]).resolve()
    if not reference.is_relative_to(root):
        raise ValueError("声音参考必须位于音色库内")
    if sha256_file(reference) != voice["reference_sha256"]:
        raise ValueError(f'{voice["id"]} 声音参考校验失败，请恢复原始 WAV')
    with wave.open(str(reference), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getframerate() != 24000:
            raise ValueError(f'{voice["id"]} 参考须为单声道 24kHz WAV')
        if audio.getnframes() == 0:
            raise ValueError(f'{voice["id"]} 参考为空')
    text = catalog["reference_texts"][voice["reference_text_key"]]
    if not text.strip():
        raise ValueError("参考台词为空")
    return reference, text


def model_identity(model_dir):
    """Verify the complete weight layout before inference, including sharded models."""
    index = model_dir / "model.safetensors.index.json"
    names = ["config.json"]
    if index.is_file():
        mapping = json.loads(index.read_text(encoding="utf-8")).get("weight_map")
        if not isinstance(mapping, dict) or not mapping or not all(
                isinstance(name, str) for name in mapping.values()):
            raise ValueError("模型分片索引缺少有效 weight_map")
        names += ["model.safetensors.index.json"] + sorted(set(mapping.values()))
    else:
        names += ["model.safetensors"]
    identity = {}
    for name in names:
        path = (model_dir / name).resolve()
        if not path.is_relative_to(model_dir.resolve()) or not path.is_file():
            raise ValueError(f"模型权重或配置缺失／越界：{name}")
        identity[name] = sha256_file(path)
    return identity


def protect_outputs(paths, catalog_path, voices):
    protected = [catalog_path] + [
        (catalog_path.parent / voice["reference_audio"]) for voice in voices.values()]
    for output in paths:
        for reference in protected:
            if output.resolve() == reference.resolve() or (
                    output.exists() and reference.exists() and os.path.samefile(output, reference)):
                raise ValueError("输出不能覆盖音色索引或任何固定声音参考（包括路径别名）")


@contextmanager
def output_reservation(output):
    """A local lock prevents two workers from publishing the same output."""
    lock = output.with_suffix(".generation.lock")
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("输出已有运行锁；先核对原任务，不能自动清理运行中的锁") from exc
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"process_identifier": os.getpid(), "started_at": time.time()}))
        yield
    finally:
        lock.unlink(missing_ok=True)


def publish_pair(output, audio, sample_rate, metadata, soundfile_module, overwrite=False):
    """Publish WAV+JSON with JSON as commit receipt; rollback exceptions before completion."""
    metadata_path = output.with_suffix(".json")
    state_path = output.with_suffix(".generation-status.json")
    with tempfile.TemporaryDirectory(prefix=".voice-", dir=output.parent) as staging:
        temporary = Path(staging)
        wav_path, json_path = temporary / "audio.wav", temporary / "metadata.json"
        soundfile_module.write(str(wav_path), audio, sample_rate, subtype="PCM_16")
        with wave.open(str(wav_path), "rb") as stream:
            if stream.getnframes() == 0 or stream.getnchannels() != 1:
                raise ValueError("临时WAV验证失败")
        metadata["output_sha256"] = sha256_file(wav_path)
        metadata["publication_status"] = "complete"
        json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        backups = []
        published = []
        state_path.write_text(json.dumps({
            "status": "publishing", "retry": "inspect_original_output",
            "staging_directory": temporary.name, "output_file": output.name,
            "metadata_file": metadata_path.name,
        }),
                              encoding="utf-8")
        try:
            for destination in (output, metadata_path):
                if destination.exists():
                    if not overwrite:
                        raise ValueError("输出已存在")
                    backup = temporary / (destination.name + ".previous")
                    os.replace(destination, backup)
                    backups.append((backup, destination))
            for source, destination in ((wav_path, output), (json_path, metadata_path)):
                os.replace(source, destination)
                published.append(destination)
            state_path.write_text(json.dumps({"status": "complete", "output_sha256": metadata["output_sha256"]}),
                                  encoding="utf-8")
        except BaseException:
            for destination in reversed(published):
                destination.unlink(missing_ok=True)
            for backup, destination in backups:
                os.replace(backup, destination)
            state_path.write_text(json.dumps({"status": "failed", "retry": "inspect_original_output"}),
                                  encoding="utf-8")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--list", action="store_true", help="列出候选及原声对照")
    parser.add_argument("--check", action="store_true", help="校验所有参考与候选分组")
    parser.add_argument("--voice-id", help="VM01—VM05、VF01—VF05、NM01/NF01 或 T00")
    text_group = parser.add_mutually_exclusive_group()
    text_group.add_argument("--text")
    text_group.add_argument("--text-file", type=Path)
    parser.add_argument("--model-dir", type=Path, help="已下载的 Qwen3-TTS 1.7B Base 目录")
    parser.add_argument("--output", type=Path, help="输出 WAV，父目录须已存在")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--preflight", action="store_true", help="仅检查参考、权重和输出，不运行GPU")
    parser.add_argument("--batch-file", type=Path, help="JSON 台词表，复用一次模型加载")
    args = parser.parse_args()
    catalog_path = args.catalog.resolve()
    catalog, voices = read_catalog(catalog_path)

    if args.list:
        print(json.dumps([{"id": v["id"], "group": v["group"], "title": v["title"]}
                          for v in voices.values()], ensure_ascii=False, indent=2))
    if args.check:
        counts = Counter(v["group"] for v in catalog["voices"])
        expected = {"male_role": 5, "female_role": 5,
                    "male_narration": 1, "female_narration": 1}
        if counts != expected or catalog["language"] != "Chinese":
            raise ValueError("候选必须为5男角色、5女角色和独立男女旁白，语言为Chinese")
        hashes = []
        for voice in voices.values():
            reference_for(catalog_path, catalog, voice)
            hashes.append(voice["reference_sha256"])
        if len(set(hashes)) != len(hashes):
            raise ValueError("发现重复参考音频")
        print(json.dumps({"status": "passed", "candidate_counts": counts,
                          "references_checked": len(hashes)}, ensure_ascii=False))
    if args.list or args.check:
        return

    if args.batch_file:
        batch = json.loads(args.batch_file.read_text(encoding="utf-8"))
        if not isinstance(batch, list) or not batch:
            parser.error("批量文件须为非空列表")
        jobs = batch
    else:
        jobs = [{"voice_id": args.voice_id, "text": args.text,
                 "text_file": str(args.text_file) if args.text_file else None,
                 "output": str(args.output) if args.output else None, "seed": args.seed}]
    prepared = []
    for job in jobs:
        if not isinstance(job, dict):
            parser.error("每条批量台词须为对象")
        prepared.append(prepare_job(job, args, catalog_path, catalog, voices, parser))
    if len({row["output"] for row in prepared}) != len(prepared):
        parser.error("批量输出路径重复")
    if args.model_dir is None:
        parser.error("生成时必须提供 --model-dir")
    model_dir = args.model_dir.resolve()
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if config.get("tts_model_type") != "base":
        parser.error("--model-dir 必须指向 Base 模型")
    weight_identity = model_identity(model_dir)
    if args.preflight:
        print(json.dumps({"status": "preflight_passed", "jobs": len(prepared),
                          "model_files": list(weight_identity)}, ensure_ascii=False))
        return
    run_jobs(prepared, args, catalog, weight_identity)


def prepare_job(job, args, catalog_path, catalog, voices, parser):
    voice_id = job.get("voice_id")
    if not isinstance(voice_id, str) or voice_id not in voices:
        parser.error("--voice-id 必须使用音色库中的固定编号")
    if job.get("text") is None and job.get("text_file") is None:
        parser.error("请提供 --text 或 --text-file")
    text = job["text"] if job.get("text") is not None else Path(job["text_file"]).read_text(encoding="utf-8")
    if not isinstance(text, str):
        parser.error("台词须为文本")
    text = text.strip()
    if not text or len(text) > 160:
        parser.error("请按句意分段，每次提供1—160个字符")
    if not isinstance(job.get("output"), str) or not job["output"]:
        parser.error("生成时必须提供 --model-dir 和 --output")
    output = Path(job["output"]).absolute()
    metadata_path = output.with_suffix(".json")
    if output.suffix.lower() != ".wav" or not output.parent.is_dir():
        parser.error("输出须为 WAV，且父目录已存在")
    protect_outputs([output, metadata_path, output.with_suffix(".generation.lock"),
                     output.with_suffix(".generation-status.json")], catalog_path, voices)
    if output.is_symlink() or metadata_path.is_symlink():
        parser.error("生成结果不能使用符号链接输出")
    if not os.access(output.parent, os.W_OK):
        parser.error("输出父目录不可写")
    if not args.overwrite and (output.exists() or metadata_path.exists()):
        parser.error("输出已存在；请换文件名，或明确使用 --overwrite")
    voice = voices[voice_id]
    reference, ref_text = reference_for(catalog_path, catalog, voice)
    if not isinstance(job.get("seed", args.seed), int) or isinstance(job.get("seed", args.seed), bool):
        parser.error("seed须为整数")
    return {"voice_id": voice_id, "text": text, "output": output,
            "voice": voice, "reference": reference, "ref_text": ref_text,
            "seed": job.get("seed", args.seed)}


def run_jobs(jobs, args, catalog, weight_identity):
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    if not torch.cuda.is_available():
        raise RuntimeError("此预设需要可用的 CUDA GPU")
    torch.set_num_threads(8)
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    model = Qwen3TTSModel.from_pretrained(
        str(args.model_dir.resolve()), device_map="cuda:0",
        dtype=torch.float16, attn_implementation="eager")
    loaded = time.monotonic()
    generation = {
        "max_new_tokens": 2048, "do_sample": True,
        "top_k": 50, "top_p": 1.0, "temperature": 0.9,
        "repetition_penalty": 1.05,
    }
    package_version = version("qwen-tts")
    for job in jobs:
        with output_reservation(job["output"]):
            generate_job(job, args, catalog, weight_identity, model, torch, np, sf,
                         generation, started, loaded, package_version)


def generate_job(job, args, catalog, weight_identity, model, torch, np, sf,
                 generation, started, loaded, package_version):
    output, voice = job["output"], job["voice"]
    torch.manual_seed(job["seed"])
    torch.cuda.manual_seed_all(job["seed"])
    line_started = time.monotonic()
    try:
        with torch.inference_mode():
            wavs, sample_rate = model.generate_voice_clone(
                text=job["text"], language=catalog["language"],
                ref_audio=str(job["reference"]), ref_text=job["ref_text"],
                x_vector_only_mode=False, **generation)
        audio = np.asarray(wavs[0], dtype=np.float32)
        generated = time.monotonic()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise RuntimeError("生成音频为空或包含无效采样")
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-5:
            raise RuntimeError("生成音频无有效声音")
        gain = min(1.0, 0.99 / peak)
        metadata = {
            "voice_id": job["voice_id"], "text": job["text"], "language": catalog["language"],
            "model": catalog["clone_model"],
            "model_file_fingerprints": weight_identity,
            "package_version": package_version,
            "reference_audio": voice["reference_audio"],
            "reference_sha256": voice["reference_sha256"], "reference_text": job["ref_text"],
            "seed": job["seed"], "compute_dtype": "float16", "attention": "eager",
            "generation": generation, "sample_rate": sample_rate,
            "duration_seconds": round(len(audio) / sample_rate, 3),
            "load_seconds": round(loaded - started, 2),
            "generation_seconds": round(generated - line_started, 2),
            "peak_gpu_memory_gigabytes": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "peak_protection_gain": gain,
            "verification": "已生成；教学语言、台词和跨段音色仍需试听核对",
        }
        publish_pair(output, audio * gain, sample_rate, metadata, sf, args.overwrite)
    except BaseException:
        output.with_suffix(".generation-status.json").write_text(
            json.dumps({"status": "failed", "retry": "inspect_original_output"}), encoding="utf-8")
        raise
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
