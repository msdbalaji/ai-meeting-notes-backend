from faster_whisper import WhisperModel
m = WhisperModel("tiny", device="cuda")
print("Whisper tiny loaded on CUDA successfully")