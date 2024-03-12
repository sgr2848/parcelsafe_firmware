greeting = 0 

safe_server_token = '1234FRED'
safe_state = 'unknown'
safe_connection_state='unknown'

network_restart = 0 
network_state = 0
network_type = 'test'
network_encryption = 'test'
network_name = 'ParcelSafe'
network_password = 'SuperSecret'
network_dhcp = '0.0.0.0'
network_subnet_mask = '0.0.0.0'
network_ip_address = '0.0.0.0'
network_gateway = '0.0.0.0'
network_dns_primary = '0.0.0.0'
network_dns_secondary = '0.0.0.0'
wifi_count = 0
wifi_request = 255
wifi_name_list = []
wifi_rssi_list = []
wifi_request_name = 'TestFred'
wifi_request_rssi = '-200 dBm'


serial_number = 'DEV-MARCUS03'
#'DEV-MARCUS03'

model =         'Advantage v1'
manufacturer =  'Parcel Safe Systems'
firmware =      '0.2.1'
firmware_cfg=   'a'

alert_low_voltage = 15.0
#should be 15.0 volts for release versions!
alert_high_box_temp = 150
alert_low_box_temp = -100
alert_high_board_temp = 150
alert_low_board_temp = -100
alert_nag_time = 300                #how often an alert repeats (seconds)

housekeeping_time = 7200             #how often housekeeping messages are sent up (in seconds)

# folder paths
jpeg_path = '/home/psafe/JPEGs/'
audio_path = '/home/psafe/Audio/Used/'

# temporary test access codes; these only work when demo_mode = True
access_test_code_list = ["1234#",
                         "5678#"]     # test access code numbers
active_mode = 17
