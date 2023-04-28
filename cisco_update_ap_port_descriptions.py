"""
@author: Nick Gendron
@description: A simple multithreaded python script to update AP port descriptions for Cisco ASWs in VLAN 920 using LLDP
@usage: Can be run via CLI by running python3 cisco_update_ap_port_descriptions.py
@notes: Input CSV file containing IP addresses of ASWs should be named input.csv and be located
withing the same directory as this script. Input file parameters can be modified at line 82. All column names should be
removed from input.csv as well. 
"""

import csv
from netmiko import ConnectHandler
import threading


def updatePortDescriptions(device):
    print("[DEBUG] Connecting to", device['ip'])
    try:
        net_connect = ConnectHandler(**device)
        print("[DEBUG] Successfully connected to", device['ip'])
        net_connect.enable()

    except Exception as e:
        print("[ERROR] Unable to connect to ", device['ip'])

    # Find interfaces in VLAN 920 and save them to a list
    print("[DEBUG] Finding interfaces in vlan 920 for", device['ip'])

    # Get a list of interfaces in vlan 920
    sendShowIntStatus = net_connect.send_command('show interfaces status vlan 920', use_textfsm=True)

    # Iterate over each interface that was found to be in VLAN 920
    for item in sendShowIntStatus:

        port = item["port"]
        status = item['status']

        print("[DEBUG] Updating description for", device['ip'], port)

        # Handling for disabled and not connected VLAN 920 interfaces
        if status == 'disabled':
            print('[WARN] Found disables interface (', port, ') skipping this interface')
            continue
        if status == 'notconnect':
            print('[WARN] Found interface that is not connected (', port, ') skipping this interface')
            continue

        # Run 'show lldp neighbor' on the current interface and save response
        neighbors = net_connect.send_command('show lldp neighbors ' + port, use_textfsm=True)
        neighbor = neighbors[0]

        # Exception handling for cases where LLDP is not enabled on the remote device/command returns nothing
        try:
            if neighbor:
                # Get the neighbor device's name and send it to formatApDesc for formatting
                neighborName = neighbors[0].get('neighbor')
                print('[DEBUG] Neighbor name found: ', neighborName)

                # Update the interface description on ASW
                net_connect.send_config_set(['interface ' + port, 'description ' + neighborName])

                print("[INFO] Successfully updated description for", device['ip'], port)

        # Throw exception for cases where LLDP is not enabled on remote device
        except Exception as e:
            print('[ERROR] Neighbor name does not exist for', device['ip'], port)

    # Write mem, disconnect, and get ready for next iteration of loops
    try:
        net_connect.send_command('write mem', use_textfsm=True)
        print("[INFO] Saved for configuration for ", device['ip'])
    except Exception as e:
        print('[ERROR] Unable to save configuration for ', device['ip'])

    net_connect.disconnect()


def main():
    username = input("Enter username: ")
    password = input("Enter password: ")
    csv_data = []
    try:
        with open('input.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            for row in reader:
                csv_data.append(row)

    except FileNotFoundError:
        print(f"File 'input.csv' not found.")

    switches = []
    for address in csv_data:
        switches.append({
            'device_type': 'cisco_ios',
            'ip': address[0],
            'username': username,
            'password': password
        })

    threads = []

    for switch in switches:
        t = threading.Thread(target=updatePortDescriptions, args=(switch,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()

