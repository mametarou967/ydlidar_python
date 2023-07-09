# -*- coding: utf-8 -*-
import serial
import queue
import threading
import sys
import select
import msvcrt


# COMポートの設定
com_port = 'COM3'  # 使用するCOMポートの指定
baud_rate = 128000  # ボーレートの指定


# シリアルポートのオープン
ser = serial.Serial(com_port, baud_rate)

# コンソールからの入力コマンド受信用
input_queue = queue.Queue()

# スレッドセーフなキューの作成
data_queue = queue.Queue()

# queue経由で受信したバイナリデータ列
data_array = bytearray()

def console_input_thread():
    while True:
        # コンソールからの入力を監視
        user_input = input()
        # 入力文字列をキューに追加
        input_queue.put(user_input)

# データ受信スレッドの定義
def receive_data_thread():
    while True:
        if ser.in_waiting > 0:
            # データの受信
            data = ser.read(ser.in_waiting)

            # キューにデータを追加
            data_queue.put(data)

            #if len(data) > 0:
            #    print(data.hex())

# キーボード入力用のスレッドの開始
console_thread = threading.Thread(target=console_input_thread)
console_thread.start()

# データ受信スレッドの開始
receive_thread = threading.Thread(target=receive_data_thread)
receive_thread.start()

# メインスレッドの実行（必要ならば終了条件を設定する）
while True:

    # コンソールからの入力コマンドの解析
    if input_queue.empty() != True :
        input_command = input_queue.get()
        print("input command is ",input_command)
        if input_command == "exit":
            break

    # キューからデータを取り出す（データがなければブロックされる）
    if(data_queue.empty() != True):
        print(data_queue.get().hex())

# シリアルポートのクローズ
ser.close()

