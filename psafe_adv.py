'''
Copyright 2022, Parcel Safe Systems

Parcel Safe, Defender Advantage code   (Feb 20 2024)
            No external camera or screen
            preserves internal camera and keypad

Filename: psafe_adv_v0.43

Current development branch: psafe_advantage_0.41

note: make sure pysftp is installed...
note: make sure paramiko is installed...

'''
local_firmware = '0.9.43'

import os
import sys
import threading
from gpiozero import LED
from gpiozero.input_devices import InputDevice
from time import sleep
import time
import string
from signal import pause
import subprocess
import logging
import ps_i2c_tvs as i2c        # psafe created module
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import socket
import json
import paramiko

# Bluezero modules
from bluezero import adapter
from bluezero import peripheral
from bluezero import device


import calendar
import datetime

import config                   # psafe created module

from lib_BLE_PSafe import *     # psafe created module

serial_number = config.serial_number
config.firmware = local_firmware+config.firmware_cfg

working_ssid = config.network_name
working_password = config.network_password

# MQTT header
msg_name       = 'dt/dfdp/v1-0/' + serial_number +'/evt'
msg_name_image = 'dt/dfdp/v1-0/' + serial_number + '/img/'
msg_name_code  = 'cmd/dfdp/v1-0/' + serial_number + '/cds'
msg_name_firmware = 'dt/dfdp/v1-0/' + serial_number + 'frm/upd'
msg_code_subscribe = 'dt/svr/' + serial_number + '/cds'
msg_door_subscribe = 'cmd/dor/' + serial_number+ '/opn'
msg_firmware_subscribe = 'cmd/frm/' + serial_number+'/upd'

alert_flag=0

door_open_type = 'unknown'
door_open_code = '000000'

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("\n\n\n\n\n")
print("Firmware (l):", local_firmware)
print("Serial Number:",config.serial_number)

try:
    os.popen('mkdir -p /home/psafe/source/downloads');
except:
    pass

os.system("sudo chmod 777 /etc/wpa_supplicant/wpa_supplicant.conf")
    

#os.system('sudo systemctl restart wpa_supplicant.service')
#sleep(2)
#os.system('sudo systemctl restart dhcpcd.service')



io_exp_out = 0x00   # intialized I/O expander output byte

io_exp_out = i2c.turn_on_red_led(io_exp_out)
sleep(0.25)
io_exp_out = i2c.turn_off_red_led(io_exp_out)
#sleep(1)
io_exp_out = i2c.turn_on_green_led(io_exp_out)
sleep(0.25)
io_exp_out = i2c.turn_off_green_led(io_exp_out)

housekeeping = 0
housekeeping_base = 0

door_open_type = 'unknown'
door_open_code = '000000'


# initialize
logging.basicConfig(level=logging.INFO)
logging.info('Initialize Keypad Version')

# folder paths
# jpeg_path = '/home/psafe/ParcelSafe/psafe-development/JPEGs/'
# audio_path = '/home/psafe/ParcelSafe/psafe-development/Audio/'


# access_code_list is set to access_test_code_list when in demo_mode = True
# otherwise it is set to supplied_access_code_list 
        
imported_access_code_list = []                  # access codes sent from server
access_code_list = imported_access_code_list    # active access code list

# init variables
access_code = ''                 # code from reading keypad scanner
input_from_keypad = ''
safe_state = 'STANDBY'
door_state = 'DOOR_CLOSED'
door_old_state='DOOR_CLOSED'
bad_code = 0                # number of invalid entered access codes
bad_code_limit = 4          # number of invalid access coeds before giving up
bad_code_lockout = 20       # number of seconds to lockout keypad adter X bad code
main_loop_count = 0
bad_code_time = 0
door_open_timer = 0         # init door open timer
door_open_timeout = 9      # door open timeout
door_mad = 45               #time before door sends nasty message after being left open
demo_mode = False           # pmm 12/16/23
time_old=0

audio_finished=0

# timeout before it asks you to enter the access code
access_code_nag_timeout = 6
access_code_nag_timer = 0
access_code_nag = False
access_code_nag_count = 0
access_code_good = 0
restart_timeout = 60

# Camera 1 settings
rotation = 180
frame_rate = 15         # frames/second
chmodcontrast = 50
exposure_val = 5
duration = 60000        # milliseconds
brightness = 55         # range: 0 to 100
saturation = -50        # range -100 (grayscale) to 100 (full color)

camera_width=1280
camera_height=960

# audio file aliases
GOOD_CODE = 'psafe_adv_correct_code_insert_package.mp3'
BAD_CODE = 'psafe_adv_incorrect_code.mp3'
BAD_CODE_LIMIT = 'psafe_adv_four_incorrect_codes.mp3'
SHUT_DOOR_1 = 'psafe_adv_push_door_shut_beep1.mp3'
SHUT_DOOR_2 = 'psafe_adv_push_door_shut_beep2.mp3'
SHUT_DOOR_3 = 'psafe_adv_push_door_shut_beep3.mp3'
NOTIFY_DOOR_OPEN = 'psafe_adv_notify_door_not_closed.mp3'
THANK_YOU_GET_OFF_PORCH = 'psafe_adv_door_is_closed_thank_get_off_porch.mp3'  # not for production code
THANK_YOU = 'psafe_adv_door_is_closed_thank_you.mp3'
WELCOME = 'psafe_adv_welcome.mp3'

# spare GPIO pins (NOT USED FOR ADVANTAGE)
# GPIO17, GPIO27, GPIO22, GPIO10, GPIO11, GPIO0, GPIO13, GPIO12, GPIO1, GPIO7, GPIO8, GPIO23

# define GPIO outputs
# GPIO 4 - UART3TxD - uart transmit to M2 module (used for Advantage Plus)
# GPIO 5 - UART3RxD - uart receive from M2 module (used for Advantage Plus)
open_door = LED(6)              # GPIO 6
# ioexp_reset_n = LED(16)         # GPIO 16
# barcode_trig_n = LED(26)        # GPIO 26

# define GPIO inputs
ioexp_int = InputDevice(5, pull_up=True)        # GPIO 5
# motion = InputDevice(13, pull_up=False)         # GPIO 13
latch_closed2 = InputDevice(24, pull_up=True)   # GPIO 24, latch switch normally closed
latch_closed1 = InputDevice(25, pull_up=True)   # GPIO 25, latch switch normally open

# init GPIO outputs
open_door.off()                 # open door command set LOW
# ioexp_reset_n.on()            # I/O expander reset set HIGH
# disp_backlight.off()            # Display backlight command set LOW
# disp_reset_n.on()             # Display reset commend set HIGH
# logging.info('Turn off barcode scanner')
# barcode_trig_n.on()             # Barcode trigger command set HIGH
# disp_data_cmd.off()            # Display data/command control set LOW

#heartburn stuff...
config_updates=0
try:
    print(config.active_mode)
except:
    cfg_new = open("/home/psafe/source/config.py", "a")
    cfg_new.write("active_mode = 0\n")
    cfg_new.close()
    config_updates=1

try:
    print(config.volume)
except:
    cfg_new = open("/home/psafe/source/config.py", "a")
    cfg_new.write("volume = 75 \n")
    cfg_new.close()
    config_updates=1

try:
    print(config.door_timeout)
except:
    cfg_new = open("/home/psafe/source/config.py", "a")
    cfg_new.write("door_timeout = 7 \n")
    cfg_new.close()
    config_updates=1

try:
    print(config.screen_width)
except:
    cfg_new = open("/home/psafe/source/config.py", "a")
    cfg_new.write("screen_width = 640 \n")
    cfg_new.close()
    config_updates=1


    
    
if(config_updates==1):
    print("Updating config file.  Getting ready to reboot.")
    sleep(3)
    subprocess.run(['sudo','reboot'])
    


door_open_timeout=config.door_timeout

camera_width=int(config.screen_width / 8) * 8    #this forces the width to be a multiple of 8
camera_height=int(camera_width * 0.75)

def force_setup():
    configure_wifi("ParcelSafe","SuperSecret")
    cfg_new= open("/home/psafe/source/cfg_new.py", "w")
    with open("/home/psafe/source/config.py", "r") as cfg_old:
        raw=cfg_old.readlines()
        for x in range(len(raw)):
            tag=raw[x].split('=')[0].strip()
            change=0
            try:
                data=raw[x].split('=')[1]
            except:
                data=''
                tag=raw[x]
            if(tag=='serial_number'):
                data="'PSX-XX'"
                change=1
            if(tag=='active_mode'):
                data=0
                change=1
            if(change==1):
                qwe=tag+' = '+str(data)+"\n"
                cfg_new.write(qwe)
                
            else:
                cfg_new.write(raw[x])
        cfg_old.close()
    cfg_new.close()
    do_it="cp /home/psafe/source/cfg_new.py /home/psafe/source/config.py"
    os.system(do_it)
    sleep(1)
    subprocess.run(['sudo','reboot'])
    
def force_serial_number(new_serial):
    configure_wifi("ParcelSafe","SuperSecret")
    cfg_new= open("/home/psafe/source/cfg_new.py", "w")
    with open("/home/psafe/source/config.py", "r") as cfg_old:
        raw=cfg_old.readlines()
        for x in range(len(raw)):
            tag=raw[x].split('=')[0].strip()
            change=0
            try:
                data=raw[x].split('=')[1]
            except:
                data=''
                tag=raw[x]
            if(tag=='serial_number'):
                data=new_serial
                change=1
            if(tag=='active_mode'):
                data=17
                change=1
            if(change==1):
                qwe=tag+' = '+str(data)+"\n"
                cfg_new.write(qwe)
            else:
                cfg_new.write(raw[x])
        cfg_old.close()
    cfg_new.close()
    do_it="cp /home/psafe/source/cfg_new.py /home/psafe/source/config.py"
    os.system(do_it)
   
    print("new serial flash")
    sleep(1)
    print(new_serial)
    sleep(10)
    subprocess.run(['sudo','reboot'])



# read input from keypad
def read_keypad():
    global access_code,greeting
    while True:
        keypad_read = i2c.keypad_scanner_read(20)
        if (keypad_read != ''):
            access_code = keypad_read
            keypad_read = ''
        sleep(0.1)

# Threading declaration ======================================================
key_read_thread = threading.Thread(target=read_keypad)
key_read_thread.start()

# Network utils
def pull_network_info():
    info=os.popen('ifconfig wlan0 | grep inet').read().split()
    config.network_ip_address = info.pop(1)
    config.network_subnet_mask = info.pop(3)
    print()
    print('Network')
    print(config.network_ip_address)
    print()


# intialize keypad
i2c.keypad_scanner_setup()

def pull_wifi():
    global working_ssid,working_password
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "r") as wifi_cfg:
        raw_cfg=wifi_cfg.readlines()
        raw_len=len(raw_cfg)
        for x in range(raw_len):
            tag=raw_cfg[x].strip().split('"')[0]
            if(tag=='ssid='):
                working_ssid=raw_cfg[x].strip().split('"')[1]
            if(tag=='psk='):
                working_password=raw_cfg[x].strip().split('"')[1]
            
        wifi_cfg.close()
    print("\n\nWorking WiFi: ",working_ssid,working_password)


# functions =======================================================
def configure_wifi(ssid, password):
    config_lines = [
        'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev',
        'update_config=1',
        'country=US',
        '\n',
        'network={',
        '\tssid="{}"'.format(ssid),
        '\tpsk="{}"'.format(password),
        '}'   
        ]
    config = '\n'.join(config_lines)
    
    #give access and writing. may have to do this manually beforehand
    os.system("sudo chmod 777 /etc/wpa_supplicant/wpa_supplicant.conf")
    
    #writing to file
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as wifi:
        wifi.write(config)
    
    print("Wifi config added. Refreshing configs")
    ## refresh configs
    os.system("sudo ip link set wlan0 down")
    sleep(1)
    os.system("sudo ip link set wlan0 up")
    sleep(0.1)
    #os.popen("sudo wpa_cli -i wlan0 reconfigure")
    os.system("sudo systemctl restart wpa_supplicant.service")
    sleep(0.1)
    os.system("sudo systemctl restart dhcpcd.service")
    #sleep(1)
    
  



# mqqt connectivity
def on_connect(client,userdata,flags,rc):
    print('Connecting . . .')
    if(str(rc) == '0'):
        print("Succesfully connected to Parcel Safe server as:",config.serial_number)
    client.subscribe("cmd/evt/" +serial_number+ "/ack")
    #client.subscribe("cmd/evt/DEV-0001/ack")
    client.subscribe(msg_code_subscribe)
    client.subscribe(msg_door_subscribe)
    client.subscribe(msg_firmware_subscribe)
    

def publish_firmware(firmware_version):
    print("Publishing firmware")
    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple())
    #msg_id=str(utc_time%100000000)
    msg_id=str(int(time.time()*1000))
    
    msg1='{"version":' + firmware_version + '}'
    try:
        publish.single(msg_name_firmware,msg1,hostname="connect.parcelsafesystems.com")
    except:
        print('Cannot push firmware notification')


def publish_basic_status():
    global can_connect
    print("\nPublish basic status")
    date = datetime.datetime.utcnow()
    msg_id=str(int(time.time()*1000))
    msg1='{"id":' + msg_id + ',"type":"env","timestamp":"' +date.isoformat("T","seconds") +'Z","data":{'
    msg1= msg1+ '"voltage":'+str(system_voltage)+','
    msg1= msg1+ '"box_temp":'+str(box_temperature)+','
    msg1= msg1+ '"board_temp":'+str(board_temperature)+'} }'
    #print(msg_name)
    #print(msg1)
    try:
        publish.single(msg_name,msg1, hostname = "connect.parcelsafesystems.com")
    except:
        can_connect = 0
        print("fail on env alert message.  v2")

def publish_event(thing):
    global can_connect
    global door_open_code
    global door_open_type
    print("\nPublish "+thing+" message")
    date = datetime.datetime.utcnow()
    msg_id=str(int(time.time()*1000))
    if(thing != 'dop'):
        msg1='{"id":' + msg_id + ',"type":"'+thing+'","timestamp":"' +date.isoformat("T","seconds") +'Z"}'
    
    if(thing == 'dop'):
        msg1='{"id":' + msg_id + ',"type":"'+thing+'","timestamp":"' +date.isoformat("T","seconds") +'Z","data":{'
        msg1 = msg1+'"code":"' + door_open_code
        msg1 = msg1+'","type":"' + door_open_type + '"} }'
        print(msg1)
        door_open_type = 'unknown'
        door_open_code = '000000'
    
    try:
        publish.single(msg_name,msg1, hostname = "connect.parcelsafesystems.com")
    except:
        can_connect=0
        print("fail sending "+thing+" message")


               
                
                 
def publish_jpg():
    global can_connect
    with open(str(config.jpeg_path)+"test.jpg",'rb') as file:
        file_jpg=file.read()
        array_jpg=bytearray(file_jpg)
        print("Publish jpg image of inside")
        date = datetime.datetime.utcnow()
        utc_time = calendar.timegm(date.utctimetuple())
        msg_temp=msg_name_image+str(utc_time)+":jpg"
        print(msg_temp)
        try:
            publish.single(msg_temp, array_jpg, qos=1, hostname = "connect.parcelsafesystems.com")
        except:
            can_connect=0
            print("fail on sending jpg")
        

def on_message(client, userdata, msg):
    global door_open_type, door_open_code
    #print("\nIncoming message from Parcel Safe server:  " + msg.topic + " " + str(msg.payload) + "\n")
    received_msg = msg.payload
    received_msg = received_msg.decode()
    #print('\nMessage payload: ' + str(received_msg) + "\n")
    t_msg=msg.topic.split('/')
    qq=len(t_msg)-1
    if(qq>=0):
        t_msg=t_msg[qq]
    print('\nIncoming msg: ',t_msg)
    
    if('code' in received_msg):
        if('dt/svr/'+serial_number+'/cds' in msg.topic):
            y_msg = json.loads(received_msg)
            #print(received_msg)
            #print(y_msg)
            k = y_msg["data"]
            print(k)       
            for i in k["data"]:
                print(i["code"])
                if(i["code"] + "#" not in imported_access_code_list):
                    imported_access_code_list.append(i["code"] + '#')
            print("Access codes downloaded")
        #print(imported_access_code_list)
            
            
    if('cmd/dor/'+serial_number+'/opn' in msg.topic):
        door_open_type = 'api'
        y_msg = json.loads(received_msg)
        print("wombat")
        print(y_msg)
        try:
            k = y_msg["data"]
            #print(k)
            #print(k["code"])
            door_open_code=k["code"]
        except:
            print("\n no data field\n\n")
        print(door_open_type)
        print(door_open_code)
        publish_event('uac')
        open_door.on()
        sleep(0.5)
        open_door.off()
        #publish_event('dop')     #door open
        door_open_timer = 0
        
        
    
    if('cmd/frm/'+serial_number+'/upd' in msg.topic):
        #publish_firmware('0.1.2')
        try:
            y_msg = json.loads(received_msg)
            k = y_msg["data"]
            upd_protocol=k["protocol"]
            upd_host=k["host"]
            upd_port=k["port"]
            upd_user=k["user"]
            upd_pwd=k["pwd"]
            upd_version=k["version"]
            upd_file=k["firmwareFile"]
            f_temp=upd_file
            try:
                f_temp=f_temp[f_temp.rindex('/')+1:]
            except:
                pass
            upd_file_store='/home/psafe/source/downloads/'+f_temp
            upd_checksum=k["checksumFile"]
            f_temp=upd_checksum
            try:
                f_temp=f_temp[f_temp.rindex('/')+1:]
            except:
                pass
            upd_checksum_store='/home/psafe/source/downloads/'+f_temp
            
            
            pull_flag=0
            try:
                ssh.connect(upd_host, username=upd_user, password=upd_pwd, port=upd_port)
                sftp=ssh.open_sftp()
            except:
                print("Could not ssh connect to: ",upd_host)
            try:
                sftp.get(upd_file, upd_file_store)
                sftp.get(upd_checksum, upd_checksum_store)                
                print("Files received")
                pull_flag=1
                mm='md5sum '+upd_file_store+' > /home/psafe/source/downloads/check.md5'
                try:
                    os.system(mm)
                    pull_flag=2
                    print('md5sum completed')
                    try:
                        w1=open('/home/psafe/source/downloads/check.md5').read().split()[0]
                        w2=open(upd_checksum_store).read().split()[0]
                        #print(w1)
                        #print(w2)
                        if(w1==w2):
                            pull_flag=10
                            print('good checksum')
                            if('psafe_adv_' in upd_file_store):
                               print("Main_code_update!")
                               try:
                                   mm='mv '+upd_file_store+' /home/psafe/source/psafe_adv.py'
                                   os.system(mm)
                                   print('Copied!')
                                   publish_firmware(upd_version)
                                   sleep(1)
                                   subprocess.run(['sudo','reboot'])
                                   print(":)")
                               except:
                                   print('Copy to new failed.   :(') 
                        else:
                            pull_flag=-10
                    except:
                        pull_flag=-2
                        print('could not open files to test checksum')
                except:
                    pull_flag = -1
                    print(mm)
                    print('md5sum barfed')
            except:
                print("sftp barfed")
                print(upd_file)
                print(upd_file_store)
                
            print("pull flag: ", pull_flag)
            ssh.close()   
        except:
            print("Error receiving firmware update")
        
 
    
def connect_to_server():
    global client
    client.loop_forever(retry_first_connection=False)
    sleep(10)    

def pull_wifi_names():
    info=os.popen('iwlist wlan0 scan | grep SSID').read()
    config.wifi_name_list=info.split('\n')
    info_2=os.popen('iwlist wlan0 scan | grep dBm').read()
    config.wifi_rssi_list=info_2.split('\n')
    l_1=len(config.wifi_name_list)
    l_2=len(config.wifi_rssi_list)
    if(l_2<l_1):
        l_1=l_2
    config.wifi_count=l_1-1
    for x in range(config.wifi_count):
        k=config.wifi_rssi_list[x].split('-')[1].strip('"')
        j=config.wifi_name_list[x].split(':')[1].strip('"')
        if((len(j)>1) and (len(k)>1)):
            print(x,j,'-'+k)

def try_404():
    try:
        print("trying 404*")
        i2c.enable_spkr(io_exp_out)
        sleep(.01)
        qwe="espeak 404"
        os.system(qwe)
        info=os.popen('iwlist wlan0 scan | grep SSID').read()
        info=info.split('\n')

        info_2=os.popen('iwlist wlan0 scan | grep dBm').read()
        info_2=info_2.split('\n')
        print(info)
        print(info_2)
        l_1=len(info)
        l_2=len(info_2)
        print(l_1,l_2)
        if(l_2<l_1):
            l_1=l_2
        l_1=l_1-1
        if(l_1>0):
            print("!")
            for x in range(l_1):
                print(x)
                k=info_2[x].split('-')[1].strip('"')
                j=info[x].split(':')[1].strip('"')
                print(j,k)
                
                if((len(j)>1) and (len(k)>1)):
                    try:
                        print(j,'-'+k)
                        qwe="espeak "+j
                        try:
                            os.system(qwe)
                        except:
                            pass
                        qwe="espeak "+'minus'+k
                        try:
                            os.system(qwe)
                        except:
                            pass
                    except:
                        print("weird name???")    
    except:
        pass
    



# terminate processes, reset safe_state to 'STANDBY'
def terminate(io_exp_out):
    global safe_state, key, access_code

    print('Entering terminate')
    safe_state = 'STANDBY'
    access_code = ''
    # io_exp_out = 0x00 
    io_exp_out = i2c.turn_off_red_led(io_exp_out)
    io_exp_out = i2c.turn_on_green_led(io_exp_out)
    io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
    io_exp_out = i2c.disable_spkr(io_exp_out)
    
    config.greeting = 0
    
    
    door_open_type = 'unknown'
    door_open_code = '000000'

    # stop any audio
    #subprocess.Popen([
    #    'pkill',
    #    'mplayer'])

# output audio to speaker
def audio_out(msg_alias, background):
    subprocess.Popen(['pkill','mplayer'])
    vol=config.volume
    if(background == True):
        print("Threaded audio")
        audio_threading = threading.Thread(target=audio_play, args=[vol,msg_alias])
        audio_threading.start()
    else:
        print("Normal audio")
        audio_play(vol,msg_alias)
        

def audio_play(vol ,msg_alias):
    global audio_finished
    audio_finished=0
    i2c.enable_spkr(io_exp_out)
    sleep(.01)
    print(msg_alias)
    subprocess.run([
    'mplayer',
    '-volume',
    str(vol),
    '-really-quiet',
    '-noconsolecontrols',
    str(config.audio_path) + msg_alias])
    sleep(0.3)
    audio_finished=1         
             

# request available access codes from the server
def request_access_code():
    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple())
    msg_id=str(int(time.time()*1000))
    msg1='{"id":' + msg_id + '}'
    print("\nRequest access codes from server\n")
    try:
        publish.single(msg_name_code,msg1,hostname="connect.parcelsafesystems.com")
    except:
        #can_connect = 0
        print('Cannot get access codes')


# houskeeping time system
def housetime():
    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple())
    return(utc_time)
    # return (utc_time - housekeeping_base)               # try return just utc_time
                




## lockout for bare password

kk=''

if(config.serial_number=='PSX-XX'):
    print("Setting Serial Number from keypad.")
    print("Type in 6 digit serial number and press *")
    io_exp_out = i2c.turn_on_green_led(io_exp_out)
    io_exp_out = i2c.turn_on_red_led(io_exp_out)
    
dummy_serial='0'
while (config.serial_number=='PSX-XX'):
    if("*" in access_code):
        kk=access_code
        access_code=''
        q2="".join(c for c in kk if c.isdigit())
        lq2=len(q2)
        #print(kk,q2,lq2)
        if(lq2 != 6):
            print("Got: ",q2)
            print("Needs to be 6 digits long.  Got",lq2,"digits")
            io_exp_out = i2c.turn_on_red_led(io_exp_out)
            dummy_serial='0'
        else:
            dummy_serial=q2
            io_exp_out = i2c.turn_off_red_led(io_exp_out)
            print("Got: ",dummy_serial,"   Press # to confirm ")
    if("#" in access_code):        
        if(len(dummy_serial)==6):
            dummy_serial="'PSX-"+dummy_serial+"'"
            print(dummy_serial)
            force_serial_number(dummy_serial)
            
    sleep(0.05)     
        
    

# this stuff has to come after the 'mqtt connectivity' defs above
# and before the 'connectivity_thread' below  
client = mqtt.Client(client_id=serial_number,clean_session=True)
client.on_connect = on_connect
client.on_message = on_message

# not how we actually want to trap this, but it is a quick start...
# we want to add the BLE stuff to configure it correctly.
ada= list(adapter.Adapter.available())[0].address



ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print('BLE: ',ada)
ble_op_thread = threading.Thread(target=main_ble, args=[ada])
ble_op_thread.start()



kk="bluetoothctl system-alias "+config.serial_number
os.popen(kk)
os.popen("sudo hciconfig hci0 sspmode 1")
os.popen("sudo hciconfig hci0 noauth")






## wombat!    remove after testing!!!!
#configure_wifi('ParcelSafe','SuperSecret')

pull_wifi()
pull_wifi_names()
print(config.wifi_name_list)

config.network_name=working_ssid
config.network_password=working_password


can_connect = 0
config.network_state = can_connect

while can_connect == 0:
    if(config.wifi_request==250):
        pull_wifi_names()
        config.wifi_request=255
        
    try:
        pull_network_info()
    except:
        pass
    try:
        client.connect("connect.parcelsafesystems.com", 1883, 60)
        can_connect = 1
        config.network_state = 1
        pull_network_info()
    except:
        print(config.network_name)
        print(config.network_password)
        print("Attempting to connect to Parcel Safe server from cold start...")
        if(config.network_restart == 1):
            print("Network restart triggered.")
            config.network_restart = 0
            configure_wifi(config.network_name,config.network_password)
            sleep(1)
    print("Access code: ", access_code)
    if(str('123456*') in access_code):          # this keypad input will put it in demo mode
        demo_mode = True
        print("Access code: ", access_code)
        break
    if(str('666*') in access_code):         # restart
        print("exiting...")
        subprocess.run(['sudo','reboot'])

    if(str('404*') in access_code):         
        try_404()
        access_code=''

    sleep(1)
    

i2c.enable_spkr(io_exp_out)
sleep(.01)
qwe="espeak connected"
os.system(qwe)


# MQTT headers reset in case serial number has changed.
serial_number=config.serial_number
msg_name       = 'dt/dfdp/v1-0/' + serial_number +'/evt'
msg_name_image = 'dt/dfdp/v1-0/' + serial_number + '/img/'
msg_name_code  = 'cmd/dfdp/v1-0/' + serial_number + '/cds'




# Threading declaration ======================================================
connectivity_thread = threading.Thread(target=connect_to_server)
connectivity_thread.start()    

    

    
###############################################################################
# begin main loop =============================================================
###############################################################################
#
io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
io_exp_out = i2c.turn_on_green_led(io_exp_out)

system_voltage = i2c.read_system_voltage()
box_temperature = i2c.read_box_temperature()
board_temperature = i2c.read_board_temperature()

housekeeping_base=housetime()
alerts=0
alert_flag=0
alert_time_to_nag=0

pull_network_info()

pull_wifi()

config.network_name=working_ssid


print("Serial number:  ",serial_number)

print('Enter main loop')


request_access_code()

publish_basic_status()

if (latch_closed2.is_active == True):
        door_state = 'DOOR_OPEN'
        door_open_timer=0
latch_old = latch_closed2.is_active

tick_tock=0

while True:
    #change it to free running and update the counter every new second
    tk = int(time.time())
    if (tk != time_old):
        main_loop_count += 1
        time_old=tk
        tick_tock=1
        
    if(demo_mode == True):
        access_code_list = config.access_test_code_list
    else:
        access_code_list = imported_access_code_list
        
   # if(str('123456*') in access_code):      # puts safe in demo mode
   #     demo_mode = True
   #    print("Enter demo mode")
   #     access_code = []
    if(str('666*') in access_code):      # forces reset
        subprocess.run(['sudo',
                        'reboot'])
    if(str('555*') in access_code):         # request access code from server
        request_access_code()
        access_code = ''

    if(str('404*') in access_code):         # restart
        try_404()
        access_code=''


    if(str('314159*') in access_code):         # reset serial number to PSX-XX
        access_code=''
        if(config.active_mode!=17):
            force_setup()
        kk=config.serial_number.split('-')[0]
        print(kk)
        if(kk=='DEV'):
            force_setup()
            
        

    if(str('911*') in access_code):         # request test firmware from server
        access_code = ''
        ssh.connect('ftp.parcelsafesystems.com', username='firmware', password='F1rmw@r3', port=2222)
        sftp=ssh.open_sftp()
        try:
            pull_flag=0
            sftp.get('/advantage/psafe_adv_panic.py', '/home/psafe/source/test_incoming.py')
            print("File received")
            pull_flag=1
            try:
                subprocess.run(['cp','/home/psafe/source/test_incoming.py','/home/psafe/source/psafe_adv.py'])
                print("File copied.")
                pull_flag=2
            except:
                pass
            if(pull_flag==2):
                ssh.close()
                io_exp_out = i2c.turn_off_red_led(io_exp_out)
                io_exp_out = i2c.turn_off_green_led(io_exp_out)

                for x in range(4):
                    io_exp_out = i2c.turn_on_red_led(io_exp_out)
                    sleep(0.2)
                    io_exp_out = i2c.turn_off_red_led(io_exp_out)
                    io_exp_out = i2c.turn_on_green_led(io_exp_out)
                    sleep(0.2)
                    io_exp_out = i2c.turn_off_green_led(io_exp_out)
                
                io_exp_out = i2c.turn_off_red_led(io_exp_out)
                subprocess.run(['sudo','reboot'])
            print('flags: ',pull_flag)
        except:
            print("SFTP failed")
        ssh.close()   
   
   
   
    housekeeping = housetime() - housekeeping_base   # housekeeping is independent from the main loop counter so they don't step on each other
    

    # if we have lost connection, every ten seconds try and bring it back up
    # at this point it still has BLE on and will take info from it...
    if ((housekeeping % 5 == 0) and (can_connect == 0) and (tick_tock==1)):
        config.network_state = 0
        io_exp_out = i2c.turn_off_green_led(io_exp_out)
        io_exp_out = i2c.turn_on_red_led(io_exp_out)
        try:
            client.connect("connect.parcelsafesystems.com", 1883, 60)
            can_connect = 1
            config.network_state = 1
            pull_network_info()
            io_exp_out = i2c.turn_on_green_led(io_exp_out)
            io_exp_out = i2c.turn_off_red_led(io_exp_out)
        
        except:
            print("Attempting to connect to Parcel Safe server from running safe...")
            print("Using ssid:",working_ssid)
            print("Using password:",working_password)
            if(config.network_restart == 1):
                #super wombat
                working_ssid = config.network_name
                working_password = config.network_password
                print("Restarting network config")
                config.network_restart = 0
                configure_wifi(working_ssid,working_password)
                
    
    #if things are out of bounds, we need to do things
    if (housekeeping % 20 == 0):
        system_voltage = i2c.read_system_voltage()
        box_temperature = i2c.read_box_temperature()
        board_temperature = i2c.read_board_temperature()
        alert_flag=0
        alert_list=[]
        if (system_voltage<=config.alert_low_voltage):
            alert_flag=1
            alert_list.append("Low Voltage "+str(system_voltage))
        if (box_temperature>=config.alert_high_box_temp):
            alert_flag=1
            alert_list.append("High Box Temperature")
        if (box_temperature<=config.alert_low_box_temp):
            alert_flag=1
            alert_list.append("Low Box Temperature")
        if (board_temperature>=config.alert_high_board_temp):
            alert_flag=1
            alert_list.append("High Board Temperature")
        if (board_temperature<=config.alert_low_board_temp):
            alert_flag=1
            alert_list.append("Low Board Temperature")
        
        if(alert_flag == 0):
            alerts=0
        else:
            if(alerts == 0):
                alert_time_to_nag= housetime()
                print("")
                print('Alerts: ')
                for x in range(len(alert_list)):
                    print(alert_list[x])
            alerts = 1


    # if we are past the alert nag time, we send a new alert
    # since a NEW alerts starts with the current time, this will fire once
    # and then wait "config.alert_nag_time" seconds before repeating itself
    if ((housetime() >= alert_time_to_nag) and (alerts !=0)):
        alert_time_to_nag = housetime() + config.alert_nag_time
        print("")
        print("Publish event on temperatures or voltages")
        print("Alert level:",alerts)
        print(alert_list)
        date = datetime.datetime.utcnow()
        utc_time = calendar.timegm(date.utctimetuple())
        msg_id=str(utc_time%10000000)
        msg1='{"id":' + msg_id + ',"type":"env","timestamp":"' +date.isoformat("T","seconds") +'Z","data":{'
        msg1= msg1+ '"voltage":'+str(system_voltage)+','
        msg1= msg1+ '"box_temp":'+str(box_temperature)+','
        msg1= msg1+ '"board_temp":'+str(board_temperature)+'} }'
        
        #print(msg1)
        try:
            publish.single(msg_name,msg1, hostname = "connect.parcelsafesystems.com")
        except:
            print("fail on env alert message.  v1")
            can_connect = 0 

        


    if (housekeeping > config.housekeeping_time):
        housekeeping_base=housetime()
        alerts=0                                    #force alerts back to 0 to make them reset the nag timer
                                                    #this is paranoid, but reliable
        #if(alert_time_to_nag > config.housekeeping_time):    #make sure we don't lose our alerts!
        #    alert_time_to_nag -= config.housekeeping_time  
        #send basic status
        publish_basic_status()
        request_access_code()
        print("UTC Time:  ", time.time())


    if ((main_loop_count > restart_timeout) and (door_state == 'DOOR_CLOSED')):
        main_loop_count = 0
        bad_code = 0
        config.greeting = 0
        access_code = ''
        io_exp_out = i2c.turn_off_red_led(io_exp_out)
        io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
        io_exp_out = i2c.turn_on_green_led(io_exp_out)
    
    # print safe state and main loop count every 5th loop
    if ((main_loop_count % 50 == 0) and (tick_tock==1)):
        print('\rSafe state: ', safe_state, '   Door state: ', door_state, '   Loop count: ', main_loop_count, '  Housetime: ', housetime(),'  keypad:', access_code,' Greeting:',config.greeting,"  ", end='')
        
    if (safe_state == 'STANDBY'):
        
        #Okay, if we are in Standby and the door is open, then we have used either the lock or remote open
        #with the App.  If we are in this state then we will ALLOW the bluetooth to change the WiFi setup
        if((door_state=='DOOR_OPEN') and (config.network_restart == 1)):
            #super wombat
            working_ssid = config.network_name
            working_password = config.network_password
            print("Restarting network config.  Reset case.")
            print(working_ssid)
            print(working_password)
            config.network_restart = 0
            configure_wifi(working_ssid,working_password)
            can_connect=0
       
       # check if valid access code has been read
        if (str('#') in access_code):
            main_loop_count = 0
            if (access_code in access_code_list):
                access_code_good = 1                    # WE HAVE A MATCH!!!!
                access_code_nag = False
                door_open_code = access_code
                door_open_type = 'keypad'
                open_door.on()
                print("\nWe have a match!")
                bad_code = 0
                io_exp_out = i2c.turn_off_green_led(io_exp_out)
                sleep(0.25)
                io_exp_out = i2c.turn_off_red_led(io_exp_out)
                io_exp_out = i2c.turn_on_green_led(io_exp_out)
                sleep(0.1)
                #disp_backlight.off()
                sleep(0.5)
                open_door.off()
                io_exp_out = i2c.turn_off_green_led(io_exp_out)
                door_open_timer = 0
                
                sleep(0.1)
                audio_out(GOOD_CODE, True)
                
                publish_event('pma')   #pincode match
                
                #publish_event('dop')    #door open
                
                door_state = 'DOOR_OPEN'
                safe_state = 'DELIVERY'
                # safe_state = 'BC_SCAN_3'
                #sleep(0.2)
                access_code = ''

            # invalid code has been entered
            else:
                # logging.info("Keypad input DOES NOT match access code in list:")
                access_code = ''
                access_code_nag = False
                key = ''  # null keypad input

                io_exp_out = i2c.turn_on_red_led(io_exp_out)
                io_exp_out = i2c.turn_off_green_led(io_exp_out)

                bad_code += 1
                # access_code_nag = False
                request_access_code()
                
                if (bad_code < bad_code_limit):
                    access_code_nag_timer = 0
                    
                    for x in range(5):
                        io_exp_out = i2c.turn_off_kp_backlight(io_exp_out)
                        print('Turning off BL - 348')
                        sleep(0.1)
                        io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
                        sleep(0.1)
                    
                    audio_out(BAD_CODE, True)
                        
                if (bad_code >= bad_code_limit):
                    access_code_nag_timer = 0
# bad code limit vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

                    audio_out(BAD_CODE_LIMIT, False)
                    
                    publish_event('pmm')     #pincode mismatch
                    
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    io_exp_out = i2c.turn_off_green_led(io_exp_out)
                    for x in range(5*bad_code_lockout):
                        io_exp_out = i2c.turn_off_kp_backlight(io_exp_out)
                        print('Turning off BL - 348')
                        io_exp_out = i2c.turn_on_red_led(io_exp_out)
                        sleep(0.1)
                        io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
                        io_exp_out = i2c.turn_off_red_led(io_exp_out)
                        sleep(0.1)
                        access_code = ''
                    
                    bad_code = 0
                    greeting = 0
                    terminate(io_exp_out)


#do the greeting message when the first key is pressed
#    if (config.greeting == 1):
#        config.greeting = 2
#        print("\rblip: ",access_code)
#        audio_out( WELCOME, True)
        
    # door is open, increment door open timer
    #if ((latch_closed1.is_active == False) or (latch_closed2.is_active == False)):
    if (latch_closed2.is_active == True):
        door_state = 'DOOR_OPEN'
        if (tick_tock==1):
            door_open_timer += 1
           
    #else:
     #   if (latch_closed2.is_active == False):
     #       door_state = 'DOOR_CLOSED'
            
    #if (latch_closed2.is_active == True):
    #    door_state = 'DOOR_CLOSED'
        
    # open door timer
    #if(door_open_timer>door_open_timeout):
    #    #flash the lights if it is less than 4 cycles 
    #    if(door_open_timer/door_open_timeout < 4):
    #        if(door_open_timer%2 == 0):
    #            io_exp_out = i2c.turn_on_red_led(io_exp_out)
    #        else:
    #            io_exp_out = i2c.turn_off_red_led(io_exp_out)
    #    if(count >= 4):
    #        pass
        # io_exp_out = i2c.turn_on_green_led(io_exp_out)
        #    print("")
    
    if(door_state == 'DOOR_CLOSED'):
        whine=0
        
    if ( ( (door_open_timer % door_open_timeout) == 0) and (door_state == 'DOOR_OPEN') ):
                
        count = int(door_open_timer/door_open_timeout)
        door_open_timer += 1
        #door left open.  call home every 15 minutes
        if(door_open_timer >(15*60+door_mad)):
            door_open_timer=door_mad+1
            publish_event('daj')       #door ajar
            
                                    
        if(door_open_timer >= door_mad):
            if(whine==0):
                audio_out(NOTIFY_DOOR_OPEN, False)
                whine=1
                publish_event('daj')       #door ajar
                
        if((door_open_timer >= door_open_timeout) and (door_open_timer < door_mad)):
            audio_out(SHUT_DOOR_1, True)
           
            
            
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # trap if the door was just closed... ususally if the system was started with
    # the door open and has now been closed.
    if ((door_state == 'DOOR_OPEN') and
        (latch_closed2.is_active == False) and (safe_state != 'DELIVERY')):
        door_state = 'DOOR_CLOSED'
        door_open_timer = 0
        #publish_event('dcl')     #door closed
        
   # door closed
    if ((door_state == 'DOOR_OPEN') and
        (latch_closed2.is_active == False) and (safe_state == 'DELIVERY')):
        door_state = 'DOOR_CLOSED'
        door_open_timer = 0
        subprocess.run([
            'pkill',
            'mplayer'])
        
        io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
        io_exp_out = i2c.turn_on_green_led(io_exp_out)
        io_exp_out = i2c.turn_off_red_led(io_exp_out)
         
        #publish_event('dcl')     #door closed
        
        
    
    debounce=latch_closed2.is_active
    sleep(0.05)
    if(latch_closed2.is_active==debounce):
        if(latch_old != debounce):
            latch_old=debounce
            if(debounce==True):
                print("\nDoor opened...")
                publish_event('dop')
            else:
                print("\nDoor closed...")
                io_exp_out = i2c.turn_on_IC_cam_LED(io_exp_out)
                if(safe_state == 'DELIVERY'):

                    if(demo_mode == True):
                        audio_out(THANK_YOU_GET_OFF_PORCH, True)
                    else:
                        audio_out(THANK_YOU, True)
        # if the audio is still going wait until it is done to turn off the last LED
        # or wait X seconds, whichever comes first
                    audio_wait=0
                    publish_event('dcl')     #door closed
                    sleep(3)
                    while ((audio_wait<40) and (audio_finished==0)):
                        sleep(0.1)
                        audio_wait+=1
                    print("wait: ",audio_wait)
                    access_code = ''
                    #io_exp_out = i2c.turn_off_IC_cam_LED(io_exp_out)
                    io_exp_out = i2c.turn_on_kp_backlight(io_exp_out)
                    terminate(io_exp_out)
                    bad_code = 0
                subprocess.run(['libcamera-still',
                        '-cs', '0',
                        '-t', '1000',
                        '-p', '1000,250,480,320',
                        '--width',str(camera_width),
                        '--height',str(camera_height),
                        '-o', str(config.jpeg_path) + 'test.jpg'])
                io_exp_out = i2c.turn_off_IC_cam_LED(io_exp_out)
                #send image over mqtt
                publish_jpg()
             
    
    
    if(config.wifi_request==250):
        pull_wifi_names()
        config.wifi_request=255
        
    config.network_state=can_connect    
    tick_tock=0

# end main loop ==================================================================

