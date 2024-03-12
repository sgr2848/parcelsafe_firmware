'''
psafe-i2c.py

Copyright 2022, Parcel Safe Systems

This module accesses the I2C devices on the Parcel Safe bezel board. In the main
program import as:

import psafe-i2c

There are currently four devices requiring I2C communication:

- NXP PCF85063A real-time clock calendar
- Maxim MAX7324AEG I/O port expander
- Microchip MCP3424T-E/SL 18-bit A/D converter
- TI TCA8418RTWR keypad scanner

The MAX7324AEG has 8 inputs and 8 outputs; the inputs and outputs have
separate I2C addresses.  The inputs have an 8-bit flag register in which
bits are set when a transition occurs (either positive or negative) on 
one of the input pins.  A 2-byte read will read both the current state of
the input pins followed by the flag register.  A bit mask can be written
to the input I2C address to selectively generate an interrupt on any
input pin transition.  The interrupt and flags are reset whenever a 
read occurs.

NOTE - 11/9/23:  smbus2 modulehas been reactivated in place of pyi2c module 
because of difficulty of the pyi2c module being located on the Pi Zero 2W.
'''


from smbus2 import SMBus, i2c_msg
from time import sleep
from gpiozero import LED
from math import log
import string
import config



# =================================================================
# start initialization
# =================================================================

# I2C DEVICE ADDRESSES
i2c_rtc_address = 0x51      # address of RTC
ioexp_out_address = 0x58    # address of I/O expander outputs
ioexp_in_address = 0x68     # address of I/O expander inputs
atod_address = 0x6A         # address of A/D converter
i2c_keypad_address = 0x34   # address of keypad scanner

# SET I/O EXPANDER RESET LINE HIGH
ioexp_reset_n = LED(16)     # GPIO 16
ioexp_reset_n.on()          # I/O expander reset set HIGH

# KEYPAD SCANNER REGISTERS
KP_GPIO1 = 0x1D     # sets row0-row3 to keypad matrix
KP_GPIO2 = 0x1E     # sets col0-col2 to keypad matrix
CFG = 0x1F          # bit0 KE_IEN (key event int enabled),
                    # bit4 INT_CFG (int deasserted after 50uS)
                    # bit7 AI (auto increment enabled)
INT_STAT = 0x02     # Interrupt status register
KEY_LCK_EC = 0x3    # key lock and event counter register
KEY_EVENT_A = 0x04  # key event A register               

# REAL TIME CLOCK
rtc_readall = []            # list for reading all rtc registers
ioexp_in = []               # list for reading I/O expander inputs, first is inputs, second is flags

# KEYPAD SCANNER
keypad_code = ''            # keypad input string
keypad_string = ''

# RTC REGISTERS
rtc_ctrl1_reg_addr = 0x01   # reset val = 0x00
                            # bit7 (EXT_TEST) 0 = normal mode, 1 = external clock test
                            # bit6 *** NOT USED ***
                            # bit5 (STOP) 0 = clock is running, 1 = clock is stopped (0x20)
                            # bit4 (SR) 0 = no software reset, 1 = initiate software reset (0x10)
                            # bit3 *** NOT USED ***
                            # bit2 (CIE) 0 = no correction interrupt generated, 
                            #            1 = interrupt pulses generated at every correction cycle
                            # bit1 (12_24) 0 = 24 hour mode, 1 = 12 hour mode
                            # bit0 (CAP_SEL) 0 = 7pF, 1 = 12.5pf 
                            
rtc_ctrl2_reg_addr = 0x01   # reset val = 0x00
                            # bit7 (AIE) alarm interrupt 0 = disabled, 1 = enabled
                            # bit6 (AF) alarm flag 0(read) = alarm flag inactive, (write) alarm flag cleared
                            #                      1(read) = alarm flag active, (write) alarm flag unchanged
                            # bit5 (MI)  minute interrupt *** NOT USED ***
                            # bit4 (HMI) half minute interrupt *** NOT USED ***
                            # bit3 (TF) timer flag *** NOT USED ***
                            # bits2:0 (COF) clock out control *** NOT USED ***
rtc_offset_reg_addr = 0x02
rtc_rambyte_reg_addr = 0x03
rtc_sec_reg_addr = 0x04
rtc_min_reg_addr = 0x05
rtc_hr_reg_addr = 0x06
rtc_days_reg_addr = 0x07
rtc_wdays_reg_addr = 0x08
rtc_mon_reg_addr = 0x09
rtc_years_reg_addr = 0x0A
rtc_sec_alarm_reg_addr = 0x0B
rtc_min_alarm_reg_addr = 0x0C
rtc_hr_alarm_reg_addr = 0x0D
rtc_day_alarm_reg_addr = 0x0E
rtc_wdays_alarm_reg_addr = 0x0F
rtc_timerval_reg_addr = 0x10
reg_timermode_reg_addr = 0x11

# I/O EXPANDER BIT MASKS
in_mask_shock = 0x01            # shock sensor input
in_mask_keypad_int = 0x02       # keypad interrupt
in_mask_I2 = 0x04
in_mask_I3 = 0x08
in_mask_I4 = 0x10
in_mask_I5 = 0x20
in_mask_I6 = 0x40
in_mask_I7 = 0x80

out_mask_GREEN_LED = 0x01
out_mask_RED_LED = 0x02         # red LED control
out_mask_RED_GREEN_LED = 0x03   # red and green LED control
out_mask_MIC = 0x04             # microphone control
out_mask_EN_SPKR = 0x08         # speaker control
out_mask_IC_CAM_LED = 0x10      # IC camera LEDs control
out_mask_KEYPAD_BL = 0x20       # kay
out_mask_OUT14 = 0x40
out_mask_OUT15 = 0x80

# NAME I2C BUS
i2cbus = SMBus(1)

# A/D CONVERTER CONFIGURATION
ADC_AVERAGES = 100
ADC_IIR_FILTER = 0.99
ADC_IIR_I_FILTER = 1.0 - ADC_IIR_FILTER

MCP3424_DEFAULT_ADDRESS = 0x6A

# MCP3424 Configuration Command Set
MCP3424_CMD_NEW_CNVRSN = 0x80           # Initiate a new conversion(One-Shot Conversion mode only)
MCP3424_CMD_MODE_CONT = 0x10            # Continuous Conversion Mode
MCP3424_CMD_MODE_ONESHOT = 0x00         # One-Shot Conversion Mode
MCP3424_CHAN1_VIN = 0x00                # chan 1, input voltage
MCP3424_CHAN2_BOX_TEMP = 0x20           # chan 2, box temp
MCP3424_CHAN3_BOARD_TEMP = 0x40         # chan 3, board temp
MCP3424_CHAN4_AIN4 = 0x60               # chan 4, spare ananlog input
MCP3424_CMD_SPS_240 = 0x00              # 240 SPS (12-bit)
MCP3424_CMD_SPS_60 = 0x04               # 60 SPS (14-bit)
MCP3424_CMD_SPS_15 = 0x08               # 15 SPS (16-bit)
MCP3424_CMD_GAIN_1 = 0x00               # PGA Gain = 1V/V
MCP3424_CMD_GAIN_2 = 0x01               # PGA Gain = 2V/V
MCP3424_CMD_GAIN_4 = 0x02               # PGA Gain = 4V/V
MCP3424_CMD_GAIN_8 = 0x03               # PGA Gain = 8V/V
MCP3424_CMD_READ_CNVRSN = 0x00          # Read Conversion Result Data

#print( i2cbus.status_code.value )

#if i2cbus.status_code.value == 1:
#    print('I2C bus is ready')

#print( i2cbus.scan() )

# =================================================================
# end intitialization
# =================================================================



# =================================================================
# start definitions
# =================================================================

# software reset of rtc
def rtc_sw_reset():
    i2cbus.write_byte(i2c_rtc_address, 0x58)

# read all the rtc time/date registers
def read_rtc_time_date_regs():
    read_block = i2cbus.read_byte_data(i2c_rtc_address, rtc_sec_reg_addr, 8)
    return read_block

# stop rtc (call before seting time)
def stop_rtc():
    ctrl_reg1 = i2cbus.read_byte_data(i2c_rtc_address, [rtc_ctrl1_reg_addr],1)
    i2cbus.writeread(i2c_rtc_address, [rtc_ctrl1_reg_addr, (ctrl_reg1 | 0x20)])

# start rtc
def start_rtc():
    ctrl_reg1 = i2cbus.writeread(i2c_rtc_address, [rtc_ctrl1_reg_addr])
    i2cbus.writeread(i2c_rtc_address, [rtc_ctrl1_reg_addr, (ctrl_reg1 & ~0x20)])

# manually enter time and date using keyboard input (ignore day of week)
def manually_set_time_date():
    # input time/date
    seconds = int(input('Input seconds: '))
    seconds = byte_to_BCD(seconds)
    minutes = int(input('Input minutes: '))
    minutes = byte_to_BCD(minutes)
    hours = int(input('Input hours: '))
    hours = byte_to_BCD(hours)
    days = int(input('Input days: '))
    days = byte_to_BCD(days)
    # weekdays = int(input('Input weekdays: '))
    months = int(input('Input months: '))
    months = byte_to_BCD(months)
    years = int(input('Input year: '))
    years = byte_to_BCD(years)
    time_date_list = [rtc_sec_reg_addr, seconds, minutes, hours, days, 0, months, years]
    print(time_date_list)
    # load rtc registers
    i2cbus.write(i2c_rtc_address, time_date_list)
    start_rtc()

# convert integer byte to BCD
def byte_to_BCD(val):
    high_val = int(val/10)
    high_val = high_val << 4
    low_val = val % 10 
    val = high_val + low_val
    return val

# convert BCD to integer
def bcd_to_byte(val):
    if val < 10:
        return val
    else:
        low_val = (0x0F & val)
        high_val = (val >> 4) * 10
    val = low_val + high_val
    return val

# green LED control
def turn_on_green_led(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_GREEN_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def turn_off_green_led(io_exp_out):
    io_exp_out = (io_exp_out & ~out_mask_GREEN_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out


# red LED control
def turn_on_red_led(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_RED_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def turn_on_redandgreen_leds(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_RED_GREEN_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def turn_off_red_led(io_exp_out):
    io_exp_out = (io_exp_out & ~out_mask_RED_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out 


# speaker control
def enable_spkr(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_EN_SPKR)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def disable_spkr(io_exp_out):
    io_exp_out = (io_exp_out & ~out_mask_EN_SPKR)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out


# keypad backlight control
def turn_on_kp_backlight(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_KEYPAD_BL)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def turn_off_kp_backlight(io_exp_out):
    io_exp_out = (io_exp_out & ~out_mask_KEYPAD_BL)
    i2cbus.write_byte(ioexp_out_address,  io_exp_out)
    return io_exp_out


# inside camera LED control
def turn_on_IC_cam_LED(io_exp_out):
    io_exp_out = (io_exp_out | out_mask_IC_CAM_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out

def turn_off_IC_cam_LED(io_exp_out):
    io_exp_out = (io_exp_out & ~out_mask_IC_CAM_LED)
    i2cbus.write_byte(ioexp_out_address, io_exp_out)
    return io_exp_out


# I/O expander read inputs
def read_io_expander_inputs():
    read = i2c_msg.read(ioexp_in_address, 2) # was i2cbus.read using pyi2c
    i2cbus.i2c_rdwr(read)
    return list (read)




# A/D converter config and read
def config_adc(channel):
    CONFIG_CMD = (MCP3424_CMD_NEW_CNVRSN | MCP3424_CMD_MODE_ONESHOT | MCP3424_CMD_SPS_240 | MCP3424_CMD_GAIN_1 | channel)
    i2cbus.write_byte(MCP3424_DEFAULT_ADDRESS, CONFIG_CMD)

def read_adc():
    data = 0
    # Read data back from MCP3424_CMD_READ_CNVRSN(0x00), 2 bytes raw_adc MSB, raw_adc LSB
    data = i2cbus.read_i2c_block_data(MCP3424_DEFAULT_ADDRESS,0,3)

    # Convert the data to 12-bits
    raw_adc = ((data[0] & 0x0F) * 256) + data[1]
    if raw_adc > 2047 :
        raw_adc -= 4095
    return (raw_adc)

def read_system_voltage():
    config_adc(MCP3424_CHAN1_VIN)
    sleep(0.01)
    raw_adc=read_adc()                      #this is a dummy read to make sure it is clear
    raw_adc=0
    for x in range(0, ADC_AVERAGES):
        raw_adc = raw_adc + read_adc()
    raw_adc= raw_adc/ADC_AVERAGES
    if (raw_adc == 0):
        raw_adc = 1
    #print('Raw voltage ADC = ',raw_adc)
    vin_volts = 0.0222*raw_adc + 0.761      # linear equation to convert code to volts
    vin_volts = round(vin_volts,2)
    return (vin_volts)


# box temperature 
def read_box_temperature(units='f'):
    config_adc(MCP3424_CHAN2_BOX_TEMP)
    sleep(0.01)
    raw_adc=read_adc()                      #this is a dummy read to make sure it is clear
    raw_adc=0
    for x in range(0, ADC_AVERAGES):
        raw_adc = raw_adc + read_adc()
    raw_adc = raw_adc/ADC_AVERAGES
    raw_adc = raw_adc * 0.62         # 0.62 is scale ratio of 2.048/3.3v
    if (raw_adc == 0):
        raw_adc = 1
    # print('Raw box ADC = ',raw_adc)
    room_temp = 298.15
    box_therm_beta = 4700
    ref_resistor = 100000
    box_res_therm = ref_resistor * ((2047/raw_adc) - 1)
    temp_k = (box_therm_beta * room_temp)/(box_therm_beta + (room_temp * log(box_res_therm / 100000)))
    box_temp_c = temp_k - 273.15
    box_temp_f = 1.8 * box_temp_c + 32
    if(units == 'c'):
        box_temp=box_temp_c
    else:
        box_temp=box_temp_f
    box_temp=round(box_temp,2)
    return (box_temp)

# board temperature
def read_board_temperature(units = 'f'):
    config_adc(MCP3424_CHAN3_BOARD_TEMP)
    sleep(0.01)
    raw_adc=read_adc()                      #this is a dummy read to make sure it is clear
    raw_adc=0
    for x in range(0, ADC_AVERAGES):
        raw_adc = raw_adc + read_adc()
    raw_adc = raw_adc/ADC_AVERAGES
    raw_adc = raw_adc * 0.62         # 0.62 is scale ratio of 2.048/3.3v
    if (raw_adc == 0):
        raw_adc = 1
    # print('Raw board ADC = ',raw_adc)
    room_temp = 298.15
    board_therm_beta = 4700
    ref_resistor = 100000
    board_res_therm = ref_resistor * ((2048/raw_adc) - 1)
    temp_k = (board_therm_beta * room_temp)/(board_therm_beta + (room_temp * log(board_res_therm / 100000)))
    # print('Temp K = ',temp_k)
    board_temp_c = temp_k - 273.15
    board_temp_f = 1.8 * board_temp_c + 32
    if(units == 'c'):
        board_temp=0
    else:
        board_temp=board_temp_f
    
    board_temp=round(board_temp,2)
    return (board_temp)
   


    # spare analog input
def read_spare_adc():
    config_adc(MCP3424_CHAN4_AIN4)
    sleep(0.01)
    raw_adc=read_adc()                      #this is a dummy read to make sure it is clear
    raw_adc=0
    for x in range(0, ADC_AVERAGES):
        raw_adc = raw_adc + read_adc()
    raw_adc = raw_adc/ADC_AVERAGES
    if (raw_adc == 0):
        raw_adc = 1
    return (raw_adc)




# Keypad scanner setup
def keypad_scanner_setup():
    i2cbus.write_byte_data(i2c_keypad_address,KP_GPIO1,0x0F)
    i2cbus.write_byte_data(i2c_keypad_address,KP_GPIO2,0x07)
    i2cbus.write_byte_data(i2c_keypad_address,CFG,0x91)
    
# Keypad scanner read
def keypad_scanner_read(timer):
    global keypad_code
    keypad_code = ''
    key_string = ''
    # check for interrupt
    int_stat_reg = i2cbus.read_byte_data(i2c_keypad_address, INT_STAT)
    #print("int_stat_reg = ",int_stat_reg)
    int_stat_reg = (0x01 & int_stat_reg)
    # print("int_stat_reg = ", int_stat_reg)
    # if interrupt occurred, read event counter register
    if(int_stat_reg == 1):
        while(timer != 0):
            # print("Key pressed")
            key_lck_ec = i2cbus.read_byte_data(i2c_keypad_address, KEY_LCK_EC)
            # print("Key lock and event counter = ",key_lck_ec)
            for x in range(0,key_lck_ec):
                key_event = i2cbus.read_byte_data(i2c_keypad_address, KEY_EVENT_A)
                # print(key_event)
                if(key_event < 100):
                    if(key_event == 1):
                        key_string = '1'
                    elif(key_event == 2):
                        key_string = '2'
                    elif(key_event == 3):
                        key_string = '3'
                    elif(key_event == 11):
                        key_string = '4'
                    elif(key_event == 12):
                        key_string = '5'
                    elif(key_event == 13):
                        key_string = '6'
                    elif(key_event == 21):
                        key_string = '7'
                    elif(key_event == 22):
                        key_string = '8'
                    elif(key_event == 23):
                        key_string = '9'
                    elif(key_event == 31):
                        key_string = '*'
                    elif(key_event == 32):
                        key_string = '0'
                    elif(key_event == 33):
                        key_string = '#'
                    else:
                        key_string = ''
                    i2cbus.write_byte_data(i2c_keypad_address,INT_STAT, 0x1F)
                    if((key_string != '') and (config.greeting == 0)):
                        config.greeting=1
                keypad_code = keypad_code + key_string
                if(key_string == '*'):
                    i2cbus.write_byte_data(i2c_keypad_address,INT_STAT, 0x1F)
                    return keypad_code
                if(key_string == '#'):
                    i2cbus.write_byte_data(i2c_keypad_address,INT_STAT, 0x1F)
                    return keypad_code
                key_string = ''
            timer -= 1
            sleep(1)
        # keypad_code = 'NO CODE'
        i2cbus.write_byte_data(i2c_keypad_address,INT_STAT, 0x1F)
        return keypad_code 
    # print("keyread341 Keypad_code: ",keypad_code)
    # print("Key: ",key_string)
    #clear keypad interrupts
    i2cbus.write_byte_data(i2c_keypad_address,INT_STAT, 0x1F) 
    return keypad_code   

# =================================================================
# end definitions
# =================================================================

# The following code can be deleted; it's in the parcel_safe_i2c_test.py file
# =================================================================
# main
# =================================================================

# RTC TEST PROGRAM, COMMENT OUT FOR I/O EXPANDER TESTS  
''' 
This test program loads the time registers in the PCF85063A RTC from user input, 
starts the clock then reads the registers at 1 second intervals. It uses functions to
convert values from/to BCD format which the RTC uses internally.  RTC needs to be 
stopped when setting values.
'''
'''
# rtc should be stopped to set time/date
stop_rtc()    
manually_set_time_date()

while True:
    
    rtc_readall = read_rtc_time_date_regs()

    # print(rtc_readall)

    for x in range (7):
        val = rtc_readall[x]
        val = bcd_to_byte(val)
        rtc_readall.pop(x)
        rtc_readall.insert(x, val)

    print_str = "Hrs: {}  Min: {}  Sec: {}  Mon: {}  Day: {}  Yr: 20{} "      
    print(print_str.format(rtc_readall[2], rtc_readall[1], rtc_readall[0], rtc_readall[5], rtc_readall[3], rtc_readall[6]))
    rtc_readall.clear()
    print("\n")
    sleep(1)

'''
# =================================================================
'''
# I/O EXPANDER OUTPUT TEST PROGRAM, COMMENT OUT FOR RTC OR I/O EXPANDER INPUT TEST PROGRAM

# turn on red and green indicator LEDs
io_exp_out = 0x00

turn_off_green_led(io_exp_out)
turn_off_red_led(io_exp_out)

while True:
    turn_on_red_led(io_exp_out)
    sleep(1)
    turn_off_red_led(io_exp_out)
    sleep(1)
    turn_on_green_led(io_exp_out)
    sleep(1)
    turn_off_green_led(io_exp_out)
    sleep(1)
    turn_on_redandgreen_leds(io_exp_out)
    sleep(1)
    turn_off_green_led(io_exp_out)
    turn_off_red_led(io_exp_out)
    sleep(1)

    
# =================================================================
'''

# I/O EXPANDER INPUT TEST PROGRAM, COMMENT OUT FOR RTC OR I/O EXPANDER OUTPUT TEST PROGRAM
'''
x = 1
while True:
    ioexp_in = read_io_expander_inputs()
    print(x)
    x = x + 1
    print(ioexp_in)
    sleep(1)
   
'''
# =================================================================

# A/D CONVERTER TEST PROGRAM

'''
while True :
    # input voltage
    config_adc(MCP3424_CHAN1_VIN)
    sleep(0.1)
    raw_adc = read_adc()
    print("ADC count: %d" % raw_adc)
    vin_volts = 0.0222*raw_adc + 0.761      # linear equation to convert code to volts
    print("Volts: %3.1f" % vin_volts)

    print()

    # box temperature 
    config_adc(MCP3424_CHAN2_BOX_TEMP)
    sleep(0.1)
    raw_adc = read_adc() * 0.62         # 0.62 is scale ratio of 2.048/3.3v
    if (raw_adc == 0):
        raw_adc = 1
    print("ADC count: %d" % raw_adc)
    room_temp = 298.15
    box_therm_beta = 4700
    ref_resistor = 100000
    box_res_therm = ref_resistor * ((2047/raw_adc) - 1)
    temp_k = (box_therm_beta * room_temp)/(box_therm_beta + (room_temp * log(box_res_therm / 100000)))
    box_temp_c = temp_k - 273.15
    print("Box temp: %3.1f" % box_temp_c)
    box_temp_f = 1.8 * box_temp_c + 32
    print("          %3.1f" % box_temp_f)

    print()

    # board temperature
    config_adc(MCP3424_CHAN3_BOARD_TEMP)
    sleep(0.1)
    raw_adc = read_adc() * 0.62         # 0.62 is scale ratio of 2.048/3.3v              
    print("ADC count: %d" % raw_adc)

    room_temp = 298.15
    board_therm_beta = 4700
    ref_resistor = 100000
    
    board_res_therm = ref_resistor * ((2048/raw_adc) - 1)
    temp_k = (board_therm_beta * room_temp)/(board_therm_beta + (room_temp * log(board_res_therm / 100000)))
    board_temp_c = temp_k - 273.15
    print("Board temp: %3.1f  " % board_temp_c)
    board_temp_f = 1.8 * board_temp_c + 32
    print("            %3.1f" % board_temp_f)

    print()

    # spare analog input
    config_adc(MCP3424_CHAN4_AIN4)
    sleep(0.1)
    raw_adc = read_adc()
    print("ADC count: %d" % raw_adc)
    print("Spare analog input ", raw_adc)

    print()

    print(" ********************************* ")

    print()
    sleep(3)
'''