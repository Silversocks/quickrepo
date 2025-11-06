#!/usr/bin/env python

from __future__ import print_function

from random import randint, choice, random
import time
import threading
import socket
import struct

import logging as log
import getopt, sys

import can
from can.bus import BusState

# TCP Server for inter-process communication on Windows
TCP_HOST = '127.0.0.1'
TCP_PORT = 55555

client_sockets = []
server_socket = None
incoming_requests = []
request_lock = threading.Lock()

def start_tcp_server():
    """Start TCP server to forward CAN messages"""
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((TCP_HOST, TCP_PORT))
    server_socket.listen(5)
    log.info(f"TCP server listening on {TCP_HOST}:{TCP_PORT}")
    
    while True:
        try:
            client, addr = server_socket.accept()
            client_sockets.append(client)
            log.info(f"Client connected from {addr}")
            
            # Start thread to receive requests from this client
            recv_thread = threading.Thread(target=receive_from_client, args=(client,), daemon=True)
            recv_thread.start()
        except:
            break

def receive_from_client(client):
    """Receive CAN requests from OBD reader via TCP"""
    while True:
        try:
            data = client.recv(13)
            if len(data) == 13:
                arb_id, dlc, msg_data = struct.unpack('<I B 8s', data)
                msg = can.Message(
                    arbitration_id=arb_id,
                    data=msg_data[:dlc],
                    is_extended_id=False
                )
                with request_lock:
                    incoming_requests.append(msg)
        except:
            break
    
    # Remove disconnected client
    if client in client_sockets:
        client_sockets.remove(client)

def broadcast_can_message(msg):
    """Send CAN message to all connected clients"""
    # Pack: arbitration_id (4 bytes), dlc (1 byte), data (8 bytes)
    data = struct.pack('<I B 8s', msg.arbitration_id, len(msg.data), bytes(msg.data).ljust(8, b'\x00'))
    
    disconnected = []
    for client in client_sockets:
        try:
            client.sendall(data)
        except:
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        client_sockets.remove(client)

# Global list of active DTCs
active_dtcs = []

# Common OBD-II DTCs (powertrain codes)
DTC_POOL = [
    (0x01, 0x33),  # P0133 - O2 Sensor Circuit Slow Response
    (0x01, 0x71),  # P0171 - System Too Lean (Bank 1)
    (0x01, 0x74),  # P0174 - System Too Lean (Bank 2)
    (0x03, 0x00),  # P0300 - Random/Multiple Cylinder Misfire
    (0x03, 0x01),  # P0301 - Cylinder 1 Misfire
    (0x04, 0x20),  # P0420 - Catalyst System Efficiency Below Threshold
    (0x04, 0x40),  # P0440 - EVAP System Malfunction
    (0x05, 0x62),  # P0562 - System Voltage Low
]

def service1(bus, msg):
    response = None
    if msg.data[2] == 0x00:
        log.debug(">> Caps")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x06, 0x41, 0x00, 0xBF, 0xDF, 0xB9, 0x91],
          is_extended_id=False)
    elif msg.data[2] == 0x04:
        log.debug(">> Calculated engine load")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x04, 0x20],
          is_extended_id=False)
    elif msg.data[2] == 0x05:
        log.debug(">> Engine coolant temperature")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x05, randint(88 + 40, 95 + 40)],
          is_extended_id=False)
    elif msg.data[2] == 0x0B:
        log.debug(">> Intake manifold absolute pressure")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x04, 0x41, 0x0B, randint(10, 40)],
          is_extended_id=False)
    elif msg.data[2] == 0x0C:
        log.debug(">> RPM")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x04, 0x41, 0x0C, randint(18, 70), randint(0, 255)],
          is_extended_id=False)
    elif msg.data[2] == 0x0D:
        log.debug(">> Speed")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x0D, randint(40, 60)],
          is_extended_id=False)
    elif msg.data[2] == 0x0F:
        log.debug(">> Intake air temperature")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x0F, randint(60, 64)],
          is_extended_id=False)
    elif msg.data[2] == 0x10:
        log.debug(">> MAF air flow rate")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x04, 0x41, 0x10, 0x00, 0xFA],
          is_extended_id=False)
    elif msg.data[2] == 0x11:
        log.debug(">> Throttle position")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x11, randint(20, 60)],
          is_extended_id=False)
    elif msg.data[2] == 0x33:
        log.debug(">> Absolute Barometric Pressure")
        response = can.Message(arbitration_id=0x7e8,
          data=[0x03, 0x41, 0x33, randint(20, 60)],
          is_extended_id=False)
    else:
        log.warning("!!! Service 1, unknown code 0x%02x", msg.data[2])
    
    if response:
        bus.send(response)  # Also send locally
    return response


def service3(bus, msg):
    """Service 0x03 - Read stored DTCs"""
    log.debug(">> Service 03: Read DTCs")
    
    if len(active_dtcs) == 0:
        # No DTCs stored
        response = can.Message(arbitration_id=0x7e8,
          data=[0x01, 0x43, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
          is_extended_id=False)
    else:
        # Send DTCs (max 3 per message)
        num_dtcs = len(active_dtcs)
        dtc_data = [0x43]  # Service response
        
        for dtc in active_dtcs[:3]:  # Max 3 DTCs per message
            dtc_data.append(dtc[0])
            dtc_data.append(dtc[1])
        
        # Pad with zeros
        while len(dtc_data) < 8:
            dtc_data.append(0x00)
        
        response = can.Message(arbitration_id=0x7e8,
          data=[len(dtc_data)-1] + dtc_data,
          is_extended_id=False)
    
    bus.send(response)
    return response


def service4(bus, msg):
    """Service 0x04 - Clear DTCs"""
    log.debug(">> Service 04: Clear DTCs")
    global active_dtcs
    active_dtcs = []
    
    response = can.Message(arbitration_id=0x7e8,
      data=[0x01, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
      is_extended_id=False)
    
    bus.send(response)
    return response


def random_dtc_generator():
    """Background thread that randomly generates DTCs"""
    global active_dtcs
    
    while True:
        time.sleep(randint(5, 10))  # Wait 5-10 seconds (increased frequency)
        
        if random() < 0.7: 
            if len(active_dtcs) < 5:  
                new_dtc = choice(DTC_POOL)
                if new_dtc not in active_dtcs:
                    active_dtcs.append(new_dtc)
                    log.info(f"*** NEW DTC: P{new_dtc[0]:02X}{new_dtc[1]:02X}")
        
        if active_dtcs and random() < 0.1:
            removed = active_dtcs.pop(randint(0, len(active_dtcs)-1))
            log.info(f"*** CLEARED DTC: P{removed[0]:02X}{removed[1]:02X}")


def receive_all():

    # Windows-friendly: Use virtual CAN bus + TCP bridge for inter-process
    bus = can.interface.Bus(interface='virtual', channel='vcan0')
    
    # Start TCP server for forwarding messages to OBD reader
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(0.5)  # Give server time to start
    
    log.info("ECU Simulator ready - waiting for requests...")
    
    #bus = can.interface.Bus(interface='socketcan',channel='can0')  # Linux only
    #bus = can.interface.Bus(interface='ixxat', channel=0, bitrate=250000)
    #bus = can.interface.Bus(interface='vector', app_name='CANalyzer', channel=0, bitrate=250000)

    #bus.state = BusState.ACTIVE
    #bus.state = BusState.PASSIVE
    
    # Start DTC generator thread
    dtc_thread = threading.Thread(target=random_dtc_generator, daemon=True)
    dtc_thread.start()
    log.info("DTC generator started - will emit random error codes every 10-30 seconds")

    try:
        while True:
            # Check for requests from local virtual CAN bus
            msg = bus.recv(0.01)
            if msg is not None:
                # Process request from local bus
                if msg.arbitration_id == 0x7df and msg.data[1] == 0x01:
                    response = service1(bus, msg)
                    if response:
                        broadcast_can_message(response)
                elif msg.arbitration_id == 0x7df and msg.data[1] == 0x03:
                    response = service3(bus, msg)
                    if response:
                        broadcast_can_message(response)
                elif msg.arbitration_id == 0x7df and msg.data[1] == 0x04:
                    response = service4(bus, msg)
                    if response:
                        broadcast_can_message(response)
                else:
                    log.warning("Unknown ID %d or service code 0x%02x", msg.arbitration_id, msg.data[1])
            
            # Check for requests from TCP clients
            with request_lock:
                if incoming_requests:
                    msg = incoming_requests.pop(0)
                    # Process request from TCP
                    if msg.arbitration_id == 0x7df and msg.data[1] == 0x01:
                        response = service1(bus, msg)
                        if response:
                            broadcast_can_message(response)
                    elif msg.arbitration_id == 0x7df and msg.data[1] == 0x03:
                        response = service3(bus, msg)
                        if response:
                            broadcast_can_message(response)
                    elif msg.arbitration_id == 0x7df and msg.data[1] == 0x04:
                        response = service4(bus, msg)
                        if response:
                            broadcast_can_message(response)
            
            time.sleep(0.001)  # Small delay to prevent CPU spinning

    except KeyboardInterrupt:
        pass

def usage():
    # DOTO: implement
    pass

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l:v", ["loglevel="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    loglevel = "INFO"

    for o, a in opts:
        if o == "-v":
            loglevel = "DEBUG"
        elif o in ("-l", "--loglevel"):
            loglevel = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    numeric_level = getattr(log, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    log.basicConfig(level=numeric_level)
    receive_all()

if __name__ == "__main__":
    main();
