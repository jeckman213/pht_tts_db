"""_summary_
"""
import os
import wave
import requests
from pyht import Client
from pyht.client import TTSOptions
from pyht.protos import api_pb2
import uuid


class PlayHTModule:
    """_summary_"""

    def __init__(self):
        self.play_ht_user_id = os.getenv("PLAY_HT_USER_ID")
        self.play_ht_api_key = os.getenv("PLAY_HT_API_KEY")
        # self.client = Client(user_id=self.play_ht_user_id, api_key=self.play_ht_api_key)
        self.voices = self.get_voices()

    def _bytes_to_wav(self, data_bytes, output_filename):
        """Converts byte array to a wav file

        Args:
            data_bytes (bytes): Bytes
            output_filename (str): Output file path
        """
        # Parse the header information
        riff_chunk_id = data_bytes[0:4]
        riff_chunk_size = int.from_bytes(data_bytes[4:8], byteorder="little")
        wave_id = data_bytes[8:12]
        fmt_chunk_id = data_bytes[12:16]
        fmt_chunk_size = int.from_bytes(data_bytes[16:20], byteorder="little")
        audio_format = int.from_bytes(data_bytes[20:22], byteorder="little")
        num_channels = int.from_bytes(data_bytes[22:24], byteorder="little")
        sample_rate = int.from_bytes(data_bytes[24:28], byteorder="little")
        byte_rate = int.from_bytes(data_bytes[28:32], byteorder="little")
        block_align = int.from_bytes(data_bytes[32:34], byteorder="little")
        bits_per_sample = int.from_bytes(data_bytes[34:36], byteorder="little")

        # Get the audio data
        data_chunk_id = data_bytes[36:40]
        data_chunk_size = int.from_bytes(data_bytes[40:44], byteorder="little")
        audio_data = data_bytes[44:]

        # Write the WAV file
        with wave.open(output_filename, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

    def get_voices(self):
        """Get voice via api

        Returns:
            list: List of response voice info
        """
        url = "https://api.play.ht/api/v2/cloned-voices"

        headers = {
            "accept": "application/json",
            "X-USER-ID": self.play_ht_user_id,
            "Authorization": self.play_ht_api_key,
        }

        response = requests.get(url, headers=headers, timeout=10)
        if not response.ok:
            print("Failed to get voices: " + response.text)
            return []

        return response.json()

    def get_voice(self, voice_name: str) -> dict:
        """Get voice from voices dict
            If doesn't find it the first time regrabs voices and tries again

        Args:
            voice_name (str): The name of the voice

        Returns:
            dict: The voice object from playht
        """
        voice_dict = next(
            (voice for voice in self.voices if voice["name"] == voice_name), None
        )

        if voice_dict is None:
            self.voices = self.get_voices()
            return next((voice for voice in self.voices if voice["name"] == voice_name), None)

        return voice_dict

    def upload(self, voice_name, filename, file_obj):
        """Upload voice to be processed instant

        Args:
            voice_name (str): Voice name
            filename (str): file name
            file_obj (File): File object

        Returns:
            _type_: _description_
        """
        url = "https://api.play.ht/api/v2/cloned-voices/instant"

        files = {"sample_file": (filename, file_obj, "audio/mpeg")}
        payload = {"voice_name": voice_name}
        headers = {
            "accept": "application/json",
            "X-USER-ID": self.play_ht_user_id,
            "Authorization": self.play_ht_api_key,
        }

        response = requests.post(
            url, data=payload, files=files, headers=headers, timeout=15
        )
        
        if not response.ok:
            print("Failed to upload voice")
            return None

        new_voice = response.json()
        self.voices.append(new_voice)

        return new_voice

    def delete(self, voice_name: str) -> bool:
        """Deletes voice by voice name

        Args:
            voice_name (str): Voice name

        Returns:
            bool: True if delete; False otherwise
        """
        url = "https://api.play.ht/api/v2/cloned-voices/"
        
        voice = self.get_voice(voice_name)
        if voice is None:
            return False

        payload = {"voice_id": voice["id"]}
        headers = {
            "accept": "application/json", 
            "content-type": "application/json",
            "X-USER-ID": self.play_ht_user_id,
            "Authorization": self.play_ht_api_key
        }

        response = requests.delete(url, json=payload, headers=headers, timeout=10)
        if not response.ok:
            print("Failed to delete: " + voice_name + " " + response.text)
            return False

        return True

    def say_and_download(self, voice_name: str, text: str):
        """_summary_

        Args:
            voice_name (str): Voice name
            text (str): The text to say
        """
        temp_file = str(uuid.uuid4()) + ".wav"

        client = Client(user_id=self.play_ht_user_id, api_key=self.play_ht_api_key)

        voice = self.get_voice(voice_name)
        if voice is None:
            print("Failed to get voice: " + voice_name)
            return None

        # Set the speech options
        options = TTSOptions(
            voice=voice["id"], format=api_pb2.FORMAT_WAV, quality="fast"
        )

        # Get the streams
        data = client.tts(text=text, options=options)
        data_bytes = b"".join(data)

        self._bytes_to_wav(data_bytes, temp_file)
        client.close()
        return temp_file
