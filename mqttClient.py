# ///////////////////////////////////////////////////////////////
#
# Copyright (c) 2024, royal029
#
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#
# Python version: 3.8.10
# Author: royal029
#
# ///////////////////////////////////////////////////////////////


import os
import subprocess
import configparser
import paho.mqtt.client as mqtt

import re

import warnings
# 忽略特定类型的警告
warnings.filterwarnings('ignore', category=DeprecationWarning)

HOST = "bemfa.com"
PORT = "9501"
client_id = ""

device_id = "A009"

# 示例命令1，打开窗帘映射为打开系统版本信息
msgExp = "on"
commandExp = "winver"

# 示例命令2，关闭窗帘映射为关闭系统版本信息
msgExp2 = "off"
commandExp2 = "TASKKILL /F /IM winver.exe"

# 示例命令3，窗帘打开到百分之六十映射为打开用户目录，配置文件mqtt_user_config.ini保存在此
msgExp3 = "on#60"
commandExp3 = "explorer shell:UsersFilesFolder"

# 示例命令4，窗帘打开到百分之八十映射为打开启动菜单
msgExp4 = "on#80"
commandExp3 = "explorer shell:startup"


user_profile_path = os.environ['USERPROFILE']
config_file_path = os.path.join(user_profile_path, 'mqtt_user_config.ini')

parsed_config = configparser.ConfigParser()
device_list = []

def main():
    global HOST
    global PORT
    global client_id

    if not os.path.exists(config_file_path):
        set_config()
    else:
        # 预处理
        preprocessed_content = preprocess_config_file(config_file_path)
        parsed_config.read_string(preprocessed_content)
        # 读取配置文件
        if 'UserInfo' in parsed_config:
            if 'domain' in parsed_config['UserInfo']:
                HOST = parsed_config['UserInfo']['domain']
            if 'port' in parsed_config['UserInfo']:
                PORT = parsed_config['UserInfo']['port']
            if 'client_id' in parsed_config['UserInfo']:
                client_id = parsed_config['UserInfo']['client_id']
        else:
            set_config()

    for section in parsed_config.sections():
        if section == "UserInfo": continue
        device_list.append(section)

    go_conn()

def check_input(input_str):
    # 定义正则表达式，匹配32位长度，包含a-f小写字母和0-9数字的字符串
    pattern = r'^[0-9a-f]{32}$'
    return re.match(pattern, input_str) is not None

def set_config():
    global client_id

    parsed_config.add_section('UserInfo')
    parsed_config.set('UserInfo', 'domain', HOST)
    parsed_config.set('UserInfo', 'port', PORT)
    # 创建一个无限循环来持续获取用户输入
    while True:
        input_cid = input("第一次启动，请输入私钥（4d9ec352e0376f2110a0c601a2857225）: ")
        # 检查用户输入
        if check_input(input_cid):
            break
        else:
            print("不符合规则，请重新输入")
    cid_to_use = input_cid if input_cid is not None else client_id
    client_id = cid_to_use
    parsed_config.set('UserInfo', 'client_id', cid_to_use)

    parsed_config.add_section(device_id)
    parsed_config[device_id] = {msgExp: commandExp, msgExp2: commandExp2, msgExp3: commandExp3}
    # 创建配置文件
    with open(config_file_path, 'w') as configfile:
        parsed_config.write(configfile)
        print("====================================")
        print(f"配置文件已创建：{config_file_path}")

def preprocess_config_file(file_path):
    """
    预处理配置文件，删除或合并重复的项目。

    :param file_path: 配置文件的路径
    :return: 处理后的配置文件内容字符串
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 用于存储处理后的节和键值对
    sections = {}
    current_section = None

    # 遍历配置文件的每一行
    for line in lines:
        line = line.strip()

        # 忽略空行和注释行
        if not line or line.startswith(';'):
            continue

        # 检查是否是节标题
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            sections[current_section] = {}
        else:
            # 假设每行都是一个键值对，使用等号分隔
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            # 如果键已经存在，则更新其值（这里采用了简单的覆盖策略）
            if key in sections[current_section]:
                # 如果需要保留所有值，可以改为追加到一个列表中
                # sections[current_section][key] = sections[current_section].get(key, []) + [value]
                # 但这里我们采用覆盖策略
                sections[current_section][key] = value
            else:
                sections[current_section][key] = value

    # 将处理后的节和键值对转换回配置文件的字符串格式
    preprocessed_config = []
    for section, options in sections.items():
        preprocessed_config.append(f'[{section}]')
        for key, value in options.items():
            preprocessed_config.append(f'{key} = {value}')
        preprocessed_config.append('')  # 添加空行以分隔不同的节

    return '\n'.join(preprocessed_config)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    for device in device_list:
        client.subscribe(device)

def on_message(client, userdata, msg):
    PAYLOAD = str(msg.payload.decode('utf-8'))
    print("Topic:"+msg.topic+" Message:"+PAYLOAD)
    # 遍历设备列表
    for device in device_list:
        if device != msg.topic: continue
        # 找到对应主题后执行指令
        for key, value in parsed_config[device].items():
            if PAYLOAD == key:
                subprocess.Popen(value,shell=True)

# 订阅成功
def on_subscribe(client, userdata, mid, granted_qos):
    print("On Subscribed: qos = %d" % granted_qos)

# 失去连接
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection %s" % rc)

def go_conn():
    print("====================================")
    print("域名: "+HOST)
    print("端口: "+PORT)
    print("私钥: "+client_id)
    print("设备: "+', '.join(device_list))
    print("====================================")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    client.username_pw_set("userName", "passwd")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.connect(HOST, int(PORT), 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down MQTT client...")
        client.disconnect()


main()
