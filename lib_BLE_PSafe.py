# Bluezero modules
from bluezero import adapter
from bluezero import peripheral
from bluezero import device
import config
#import os

SERVICE = "7F7D0000-4662-11EE-AC26-28C63F1DF35D"
SAFE_SERVER_TOKEN = "7F7D0100-4662-11EE-AC26-28C63F1DF35D"           #"Safe - Server access token"        Read Only
SAFE_STATE =  "7F7D0101-4662-11EE-AC26-28C63F1DF35D"           #"Safe - State"               Read Only
SAFE_CONNECTION = "7F7D0102-4662-11EE-AC26-28C63F1DF35D"        #"Safe - Connection State"    Read Only

COMMAND_NETWORK_COMMIT = "7F7D0200-4662-11EE-AC26-28C63F1DF35D" #"Command - Network Commit"
COMMAND_NETWORK_RESTART = "7F7D0201-4662-11EE-AC26-28C63F1DF35D" #"Command - Network Restart"

NETWORK_STATE = "7F7D0A00-4662-11EE-AC26-28C63F1DF35D"          #"Network - State"            Read Only
NETWORK_TYPE = "7F7D0A01-4662-11EE-AC26-28C63F1DF35D"           #"Network - Type"              Read / Write
NETWORK_WIFI_NAME = "7F7D0A02-4662-11EE-AC26-28C63F1DF35D"      #"Network - WiFi Name"         Read / Write
NETWORK_WIFI_ENCRYPTION = "7F7D0A03-4662-11EE-AC26-28C63F1DF35D"  #"Network - WiFi Encryption"     Read / Write
NETWORK_WIFI_PASSWORD = "7F7D0A04-4662-11EE-AC26-28C63F1DF35D"  #"Network - WiFi Password"     Write Only
NETWORK_DHCP =          "7F7D0A05-4662-11EE-AC26-28C63F1DF35D"           #"Network - DHCP"              Read / Write
NETWORK_IP_ADDR =       "7F7D0A06-4662-11EE-AC26-28C63F1DF35D"        #"Network - IP Address"        Read / Write; Read Only when DHCP is enabled
NETWORK_SUBNET_MASK =   "7F7D0A07-4662-11EE-AC26-28C63F1DF35D"    #"Network - Subnet Mask"       Read / Write; Read Only when DHCP is enabled
NETWORK_GATEWAY =       "7F7D0A08-4662-11EE-AC26-28C63F1DF35D"        #"Network - Gateway"           Read / Write; Read Only when DHCP is enabled
NETWORK_DNS_PRIMARY =   "7F7D0A09-4662-11EE-AC26-28C63F1DF35D"    #"Network - DNS Primary"       Read / Write; Read Only when DHCP is enabled
NETWORK_DNS_SECONDARY = "7F7D0A0A-4662-11EE-AC26-28C63F1DF35D"  #"Network - DNS Secondary"     Read / Write; Read Only when DHCP is enabled

NETWORK_SSID_COUNT =    "7F7D0A0B-4662-11EE-AC26-28C63F1DF35D"
NETWORK_SSID_REQUEST =  "7F7D0A0C-4662-11EE-AC26-28C63F1DF35D"
NETWORK_SSID_NAME =     "7F7D0A0D-4662-11EE-AC26-28C63F1DF35D"
NETWORK_SSID_RSSI =     "7F7D0A0E-4662-11EE-AC26-28C63F1DF35D"

#UUID ble_uuid_device_service = {UUID{"7F7D0000-4662-11EE-AC26-28C63F1DF35D"}};

#UUID ble_uuid_generic_access_service = {UUID{"1800"}};
#  {UUID{"2A00"}, (char*)"Generic Access - Device Name"},
#  {UUID{"2A01"}, (char*)"Generic Access - Appearance"},


#UUID ble_uuid_generic_attribute_service = {UUID{"1801"}};


#UUID ble_uuid_device_info_service = {UUID{"180A"}};
DEVICE_MODEL = "2A24"   #"Device Information - Model Number"},
DEVICE_SERIAL_NUMBER = "2A25" #"Device Information - Serial Number"
DEVICE_FIRMWARE = "2A26"  #"Device Information - Firmware Version"},
DEVICE_MANUFACTURER = "2A29"    #"Device Information - Manufacturer Name"},

class UARTDevice:
    @classmethod
    def network_name(cls, value, options):
        config.network_name = bytes(value).decode('utf-8')
        print("Name changed: ")
        print(config.network_name)
        print(value)

    @classmethod
    def network_type(cls, value, options):
        config.network_type = bytes(value).decode('utf-8')

    @classmethod
    def network_encryption(cls, value, options):
        config.network_encryption = bytes(value).decode('utf-8')

    @classmethod
    def network_password(cls, value, options):
        config.network_password = bytes(value).decode('utf-8')
        
    @classmethod
    def network_restart(cls, value, options):
        print("Restarting Network")
        config.network_restart = 1
        
    @classmethod
    def network_dhcp(cls, value, options):
        config.network_dhcp = bytes(value).decode('utf-8')

    @classmethod
    def network_subnet_mask(cls, value, options):
        config.network_subnet_mask = bytes(value).decode('utf-8')

    @classmethod
    def network_gateway(cls, value, options):
        config.network_gateway = bytes(value).decode('utf-8')

    @classmethod
    def network_ip_address(cls, value, options):
        config.network_ip_address = bytes(value).decode('utf-8')
    
    @classmethod
    def network_dns_primary(cls, value, options):
        config.network_dns_primary = bytes(value).decode('utf-8')

    @classmethod
    def network_dns_secondary(cls, value, options):
        config.network_dns_secondary = bytes(value).decode('utf-8')
        
    @classmethod
    def process_request(cls, value, options):
        print("\nwifi name & rssi request")
        tt=bytes(value)
        config.wifi_request=int.from_bytes(tt, "big")
        print(config.wifi_request)
        if((config.wifi_count > 0) and (config.wifi_request<=200) and (config.wifi_request<config.wifi_count)):
            k='-'+config.wifi_rssi_list[config.wifi_request].split('-')[1].strip('"')
            j=config.wifi_name_list[config.wifi_request].split(':')[1].strip('"')
            print(j,k)
            config.wifi_request_name=j
            config.wifi_request_rssi=k
            config.wifi_request=255      
        else:
            print(config.wifi_request)
            if(config.wifi_request!=250):
                config.wifi_request=254
        return
    
def rc_network_ip_address():
    return list(config.network_ip_address.encode('ascii'))

def read_name():
    return list(config.wifi_request_name.encode('ascii'))

def read_rssi():
    return list(config.wifi_request_rssi.encode('ascii'))

def read_request():
    return [config.wifi_request]

def read_count():
    return [config.wifi_count]



def main_ble(adapter_address):
    ble_uart = peripheral.Peripheral(adapter_address, local_name='PSAFE_UART')
    ble_uart.add_service(srv_id=1, uuid=SERVICE, primary=True)

    ble_uart.add_characteristic(srv_id=1, chr_id=1, uuid= DEVICE_MODEL,
                               value= config.model.encode('ascii') ,
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=2, uuid=DEVICE_SERIAL_NUMBER,
                                value= config.serial_number.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)
    
        
    ble_uart.add_characteristic(srv_id=1, chr_id=3, uuid=DEVICE_FIRMWARE,
                                value= config.firmware.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)
        
    ble_uart.add_characteristic(srv_id=1, chr_id=4, uuid=DEVICE_MANUFACTURER,
                                value= config.manufacturer.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=5, uuid=COMMAND_NETWORK_RESTART,
                                value=[config.network_restart], notifying=False,
                                flags=['write', 'write-without-response'],
                                write_callback=UARTDevice.network_restart,
                                read_callback= None,
                                notify_callback=None)


    ble_uart.add_characteristic(srv_id=1, chr_id=6, uuid=COMMAND_NETWORK_COMMIT,
                                value=[config.network_restart], notifying=False,
                                flags=['write', 'write-without-response'],
                                write_callback=UARTDevice.network_restart,
                                read_callback= None,
                                notify_callback=None)


    ble_uart.add_characteristic(srv_id=1, chr_id=7, uuid=NETWORK_WIFI_NAME,
                                value=config.network_name.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_name,
                                read_callback= None,
                                notify_callback=None)
    
    ble_uart.add_characteristic(srv_id=1, chr_id=8, uuid=NETWORK_WIFI_PASSWORD,
                                value=config.network_password.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_password,
                                read_callback= None,
                                notify_callback=None)
    
    ble_uart.add_characteristic(srv_id=1, chr_id=9, uuid=NETWORK_DHCP,
                                value=config.network_dhcp.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_dhcp,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=10, uuid=NETWORK_SUBNET_MASK,
                                value=config.network_subnet_mask.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_subnet_mask,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=11, uuid=NETWORK_GATEWAY,
                                value=config.network_gateway.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_gateway,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=12, uuid=NETWORK_IP_ADDR,
                                value=config.network_ip_address.encode('ascii'),
                                notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_ip_address,
                                read_callback= rc_network_ip_address,
                                notify_callback=None)
 
    ble_uart.add_characteristic(srv_id=1, chr_id=13, uuid=NETWORK_DNS_PRIMARY,
                                value=config.network_dns_primary.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_dns_primary,
                                read_callback= None,
                                notify_callback=None)
 
    ble_uart.add_characteristic(srv_id=1, chr_id=14, uuid=NETWORK_DNS_SECONDARY,
                                value=config.network_dns_secondary.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_dns_secondary,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=15, uuid=NETWORK_TYPE,
                                value=config.network_dns_secondary.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_dns_secondary,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=16, uuid=NETWORK_WIFI_ENCRYPTION,
                                value=config.network_encryption.encode('ascii'), notifying=False,
                                flags=['read','write', 'write-without-response'],
                                write_callback=UARTDevice.network_encryption,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=17, uuid=SAFE_SERVER_TOKEN,
                                value= config.safe_server_token.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=18, uuid=SAFE_STATE,
                                value= config.safe_state.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=19, uuid=SAFE_CONNECTION,
                                value= config.safe_connection_state.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=20, uuid=NETWORK_STATE,
                                value= config.network_state.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback=None,
                                read_callback= None,
                                notify_callback=None)


    ble_uart.add_characteristic(srv_id=1, chr_id=21, uuid=NETWORK_SSID_COUNT,
                                value=[config.wifi_count],
                                notifying=False,
                                flags=['read'],
                                write_callback= None,
                                read_callback= read_count,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=22, uuid=NETWORK_SSID_REQUEST,
                                value=[config.wifi_request],
                                notifying=False,
                                flags=['read','write','write-without-response'],
                                write_callback= UARTDevice.process_request,
                                read_callback= read_request,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=23, uuid=NETWORK_SSID_NAME,
                                value=config.wifi_request_name.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback= None,
                                read_callback= read_name,
                                notify_callback=None)

    ble_uart.add_characteristic(srv_id=1, chr_id=24, uuid=NETWORK_SSID_RSSI,
                                value=config.wifi_request_rssi.encode('ascii'),
                                notifying=False,
                                flags=['read'],
                                write_callback= None,
                                read_callback= read_rssi,
                                notify_callback=None)

   




    ble_uart.publish()
