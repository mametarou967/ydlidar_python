# -*- coding: utf-8 -*-
import serial
import time
from collections import deque

COM="COM3"
bitRate=128000

ser = serial.Serial(COM, bitRate, timeout=0.1)

q = deque()

while True:

	time.sleep(0.1)
	
	q.append(ser.read_all())
	result = ser.read_all()
	print(result.hex())

	if result == b'\r':	# <Enter>で終了
		break

print('program end')

ser.close()