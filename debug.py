import wave
import struct

with wave.open('test/test.wav') as f:
    assert f.getframerate() == 16000, 'Wrong audio framerate! '+str(f.getframerate())
    assert f.getsampwidth() == 2, 'Wrong sample size!'
    assert f.getnchannels() == 1, 'Only support mono!'
    samp_num = f.getnframes()
    audio = f.readframes(samp_num)

with open('test/test.txt', encoding='utf-8') as f:
    trans = f.readline().strip().encode('utf-8')

with open('debug.bin', 'wb') as f:
    f.write(struct.pack('<i', samp_num))
    f.write(audio)
    f.write(struct.pack('<i', 0))
    f.write(struct.pack('<i', len(trans)))
    print(f'Wrote {len(trans)}')
    f.write(trans)
    f.write(struct.pack('<i', 0))
    f.write(struct.pack('<i', 0))
