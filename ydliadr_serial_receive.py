# -*- coding: utf-8 -*-
import serial
import queue
import threading
import sys
import select
import msvcrt

debug_mode = False

# COMポートの設定
com_port = 'COM3'  # 使用するCOMポートの指定
baud_rate = 128000  # ボーレートの指定

# シリアルポートのオープン
ser = serial.Serial(com_port, baud_rate)

# 表示用配列
disp_array = [None] * 360

# コンソールからの入力コマンド受信用
input_queue = queue.Queue()

# スレッドセーフなキューの作成
data_queue = queue.Queue()

# queue経由で受信したバイナリデータ列
data_array = bytearray()

def debug_print(message):
    if debug_mode:
        print(message)


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

# RANGING DATA PROTOCOL CHECK
def is_ranging_data_fully_received(data):
    ph_len = 2
    ct_len = 1
    lsn_len = 1
    fsa_len = 2
    lsa_len = 2
    cs_len = 2
    # データ長部分を抽出する
    if len(data) <= 4:
        return False

    lsn = data[3]

    # データバッファがデータ長以上の長さを持っているか確認する
    sample_len = lsn * 2
    ranging_data_len = \
    ph_len + \
    ct_len + \
    lsn_len + \
    fsa_len + \
    lsa_len + \
    cs_len + \
    sample_len

    if len(data) >= ranging_data_len:
        return True
    else:
        return False 

def calc_angle(lsb,msb):
    return (((msb << 8) | lsb) >> 1) / 64

def calc_distance(lsb,msb):
    return (((msb << 8) | lsb) >> 2) # unit [mm]


def ranging_data_analayze(index,data):
    # index確定
    ph_low = data[0]
    ph_high = data[1]
    ct = data[2]
    lsn = data[3]
    fsa_low = data[4]
    fsa_high = data[5]
    lsa_low = data[6]
    lsa_high = data[7]
    cs_low = data[8]
    cs_high = data[9]

    # 要素計算
    starting_angle = calc_angle(fsa_low,fsa_high)
    end_angle = calc_angle(lsa_low,lsa_high)
    unit_angle = (end_angle - starting_angle) / lsn

    debug_print("---------------------")
    debug_print(f"index:{index}")
    debug_print(f"開始角度:{starting_angle}")
    debug_print(f"終了角度:{end_angle}")
    debug_print(f"単位角度:{unit_angle}")
    debug_print(f"サンプル数:{lsn}")

    if lsn < 1:
        return

    if starting_angle == end_angle:
        return

    loop_index = 0
    while True:
        dis_low = data[ 10 + (2 * loop_index) ]
        dis_high = data[ 10 + (2 * loop_index) + 1 ]
        
        term_distance = calc_distance(dis_low,dis_high)
        term_angle = starting_angle + unit_angle * loop_index

        debug_print(f" [{loop_index}]角度:{term_angle} 距離:{term_distance}")
        
        # 値を表示用配列に格納する
        int_term_angle = int(term_angle // 1) % 360
        disp_array[int_term_angle] = term_distance

        # indexを増加させる処理
        loop_index = loop_index + 1
        
        # 特定の値になったらループを抜ける条件
        if loop_index == lsn:
            break


# キーボード入力用のスレッドの開始
console_thread = threading.Thread(target=console_input_thread)
console_thread.start()

# データ受信スレッドの開始
receive_thread = threading.Thread(target=receive_data_thread)
receive_thread.start()

receive_index = 0
# メインスレッドの実行（必要ならば終了条件を設定する）
while True:

    # コンソールからの入力コマンドの解析
    if input_queue.empty() != True :
        input_command = input_queue.get()
        print("input command is ",input_command)
        if input_command == "exit":
            break
        elif input_command == "print4":
            print(f"角度  0:{disp_array[0]}")
            print(f"角度 90:{disp_array[90]}")
            print(f"角度180:{disp_array[180]}")
            print(f"角度270:{disp_array[270]}")
        elif input_command == "print8":
            print(f"角度  0:{disp_array[0]}")
            print(f"角度 45:{disp_array[45]}")
            print(f"角度 90:{disp_array[90]}")
            print(f"角度135:{disp_array[135]}")
            print(f"角度180:{disp_array[180]}")
            print(f"角度225:{disp_array[225]}")
            print(f"角度270:{disp_array[270]}")
            print(f"角度315:{disp_array[315]}")

    # キューからデータを取り出す（データがなければブロックされる）
    if(data_queue.empty() != True):
        data_array.extend(data_queue.get())

    # データの解析処理
    if len(data_array) > 1:
        first_byte = data_array[0]
        second_byte = data_array[1]

        if first_byte == 0xA5 and second_byte == 0x5A:
            debug_print("config コマンドを検出しました")
            # 解析ができなかったため先頭の一文字を削除
            del data_array[:1]
        elif first_byte == 0xAA and second_byte == 0x55:
            # 該当コマンドの末尾まで受信できているか確認する
            if is_ranging_data_fully_received(data_array):
                # ここで解析する
                receive_index = receive_index + 1
                ranging_data_analayze(receive_index,data_array)
                # 該当コマンドのサイズ分削除
                del_len = 10 + (data_array[3] * 2)
                del data_array[:del_len]
        else:
            # 解析ができなかったため先頭の一文字を削除
            del data_array[:1]

    # 解析結果の表示
    # print(data.hex())

    # 必要ならば特定の条件に基づいてコンソールにメッセージを表示する

# シリアルポートのクローズ
ser.close()

