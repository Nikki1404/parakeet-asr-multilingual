import riva.client
import time

AUDIO_FILE = "/home/re_nikitav/audio_maria/maria1.wav"

# gRPC endpoint from your logs
SERVER = "192.168.4.62:50051"

# Spanish language
LANGUAGE = "es-US"


def main():
    auth = riva.client.Auth(uri=SERVER)

    asr_service = riva.client.ASRService(auth)

    config = riva.client.StreamingRecognitionConfig(
        config=riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=16000,
            language_code=LANGUAGE,
            max_alternatives=1,
            enable_automatic_punctuation=True
        ),
        interim_results=True
    )

    start_time = time.time()

    with open(AUDIO_FILE, "rb") as f:
        audio_data = f.read()

    # chunk size = 80 ms
    chunk_size = 16000 * 2 * 80 // 1000

    chunks = [
        audio_data[i:i + chunk_size]
        for i in range(0, len(audio_data), chunk_size)
    ]

    print("STARTING STREAM")

    responses = asr_service.streaming_response_generator(
        audio_chunks=chunks,
        streaming_config=config
    )

    final_transcript = []

    for response in responses:
        for result in response.results:
            transcript = result.alternatives[0].transcript

            if transcript:
                print("TRANSCRIPT:", transcript)

            if result.is_final:
                final_transcript.append(transcript)

    total_time = time.time() - start_time

    print("\nFINAL TRANSCRIPT:")
    print(" ".join(final_transcript))

    print(f"\nTOTAL TIME: {total_time:.2f} sec")


if __name__ == "__main__":
    main()
