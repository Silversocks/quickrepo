#!/usr/bin/env python
"""
OBD-II Reader - Reads diagnostic data from ECU simulator

This program connects to a CAN bus and reads real-time vehicle data
from an OBD-II compliant ECU (or simulator).
Windows-compatible version using TCP bridge for inter-process communication.
"""

import can
import time
import sys
import socket
import struct
import threading

# TCP connection to ECU simulator
TCP_HOST = '127.0.0.1'
TCP_PORT = 55555

class OBDReader:
    """OBD-II diagnostic reader"""
    
    # OBD-II standard IDs
    REQUEST_ID = 0x7DF  # Broadcast to all ECUs
    RESPONSE_ID = 0x7E8  # ECU response
    
    # Service codes
    SERVICE_CURRENT_DATA = 0x01
    SERVICE_READ_DTCS = 0x03
    SERVICE_CLEAR_DTCS = 0x04
    
    def __init__(self):
        """Initialize CAN bus connection and TCP socket"""
        try:
            # Local virtual CAN for sending requests
            self.bus = can.Bus(interface='virtual', channel='vcan0')
            print(f"✓ Connected to virtual CAN bus")
            
            # TCP socket to receive responses from ECU
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((TCP_HOST, TCP_PORT))
            print(f"✓ Connected to ECU simulator at {TCP_HOST}:{TCP_PORT}")
            
            # Buffer for received responses
            self.response_queue = []
            self.response_lock = threading.Lock()
            
            # Start background thread to receive TCP messages
            self.receiver_thread = threading.Thread(target=self._tcp_receiver, daemon=True)
            self.receiver_thread.start()
            
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            print("\n⚠️  Make sure the ECU simulator is running first!")
            sys.exit(1)
    
    def _tcp_receiver(self):
        """Background thread to receive CAN messages via TCP"""
        while True:
            try:
                # Receive packed CAN message: arbitration_id (4 bytes), dlc (1 byte), data (8 bytes)
                data = self.tcp_socket.recv(13)
                if len(data) == 13:
                    arb_id, dlc, msg_data = struct.unpack('<I B 8s', data)
                    msg = can.Message(
                        arbitration_id=arb_id,
                        data=msg_data[:dlc],
                        is_extended_id=False
                    )
                    with self.response_lock:
                        self.response_queue.append(msg)
            except:
                break
    
    def send_request(self, service, pid=0x00):
        """Send OBD-II request to ECU via TCP"""
        data = [0x02, service, pid, 0x00, 0x00, 0x00, 0x00, 0x00]
        msg = can.Message(
            arbitration_id=self.REQUEST_ID,
            data=data,
            is_extended_id=False
        )
        
        # Send via TCP to simulator
        packed_data = struct.pack('<I B 8s', msg.arbitration_id, len(msg.data), bytes(msg.data).ljust(8, b'\x00'))
        try:
            self.tcp_socket.sendall(packed_data)
        except:
            pass
    
    def wait_response(self, timeout=1.0):
        """Wait for ECU response from TCP"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.response_lock:
                if self.response_queue:
                    msg = self.response_queue.pop(0)
                    if msg.arbitration_id == self.RESPONSE_ID:
                        return msg
            time.sleep(0.01)
        return None
    
    def read_rpm(self):
        """Read engine RPM (PID 0x0C)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x0C)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x0C:
            # Formula: ((A * 256) + B) / 4
            rpm = ((response.data[3] * 256) + response.data[4]) / 4
            return rpm
        return None
    
    def read_speed(self):
        """Read vehicle speed (PID 0x0D)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x0D)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x0D:
            # Formula: A (km/h)
            speed = response.data[3]
            return speed
        return None
    
    def read_coolant_temp(self):
        """Read engine coolant temperature (PID 0x05)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x05)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x05:
            # Formula: A - 40 (Celsius)
            temp = response.data[3] - 40
            return temp
        return None
    
    def read_throttle(self):
        """Read throttle position (PID 0x11)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x11)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x11:
            # Formula: (A * 100) / 255 (percentage)
            throttle = (response.data[3] * 100) / 255
            return throttle
        return None
    
    def read_engine_load(self):
        """Read calculated engine load (PID 0x04)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x04)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x04:
            # Formula: (A * 100) / 255 (percentage)
            load = (response.data[3] * 100) / 255
            return load
        return None
    
    def read_intake_temp(self):
        """Read intake air temperature (PID 0x0F)"""
        self.send_request(self.SERVICE_CURRENT_DATA, 0x0F)
        response = self.wait_response()
        
        if response and response.data[1] == 0x41 and response.data[2] == 0x0F:
            # Formula: A - 40 (Celsius)
            temp = response.data[3] - 40
            return temp
        return None
    
    def read_dtcs(self):
        """Read Diagnostic Trouble Codes (Service 0x03)"""
        # Send request with just service code via TCP
        data = [0x01, self.SERVICE_READ_DTCS, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        msg = can.Message(
            arbitration_id=self.REQUEST_ID,
            data=data,
            is_extended_id=False
        )
        
        # Send via TCP to simulator
        packed_data = struct.pack('<I B 8s', msg.arbitration_id, len(msg.data), bytes(msg.data).ljust(8, b'\x00'))
        try:
            self.tcp_socket.sendall(packed_data)
        except:
            return []
        
        response = self.wait_response()
        
        if response and response.data[1] == 0x43:
            dtcs = []
            # Parse DTCs (2 bytes each)
            for i in range(2, len(response.data)-1, 2):
                if response.data[i] != 0x00:
                    dtc_high = response.data[i]
                    dtc_low = response.data[i+1]
                    # Format as P-code (powertrain)
                    dtc_str = f"P{dtc_high:02X}{dtc_low:02X}"
                    dtcs.append(dtc_str)
            return dtcs
        return []
    
    def clear_dtcs(self):
        """Clear all Diagnostic Trouble Codes (Service 0x04)"""
        data = [0x01, self.SERVICE_CLEAR_DTCS, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        msg = can.Message(
            arbitration_id=self.REQUEST_ID,
            data=data,
            is_extended_id=False
        )
        
        # Send via TCP to simulator
        packed_data = struct.pack('<I B 8s', msg.arbitration_id, len(msg.data), bytes(msg.data).ljust(8, b'\x00'))
        try:
            self.tcp_socket.sendall(packed_data)
        except:
            return False
        
        response = self.wait_response()
        return response is not None and response.data[1] == 0x44
    
    def display_dashboard(self):
        """Display real-time dashboard with all sensor readings"""
        print("\n" + "="*60)
        print("       OBD-II DIAGNOSTIC READER - LIVE DASHBOARD")
        print("="*60)
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                print("\r" + " "*80, end='')  # Clear line
                
                # Read all parameters
                rpm = self.read_rpm()
                speed = self.read_speed()
                coolant = self.read_coolant_temp()
                throttle = self.read_throttle()
                load = self.read_engine_load()
                intake = self.read_intake_temp()
                
                # Check if ECU is responding
                if rpm is None and speed is None and coolant is None:
                    print("\r⚠️  No response from ECU - Is the simulator running?", 
                          end='', flush=True)
                    time.sleep(1)
                    continue
                
                # Display in formatted output (handle None values)
                rpm_str = f"{rpm:6.0f}" if rpm is not None else "  ----"
                speed_str = f"{speed:3.0f}" if speed is not None else "---"
                coolant_str = f"{coolant:3.0f}" if coolant is not None else "---"
                throttle_str = f"{throttle:5.1f}" if throttle is not None else " ----"
                load_str = f"{load:5.1f}" if load is not None else " ----"
                intake_str = f"{intake:3.0f}" if intake is not None else "---"
                
                print(f"\r🚗 RPM: {rpm_str} | "
                      f"Speed: {speed_str} km/h | "
                      f"Coolant: {coolant_str}°C | "
                      f"Throttle: {throttle_str}% | "
                      f"Load: {load_str}% | "
                      f"Intake: {intake_str}°C", 
                      end='', flush=True)
                
                time.sleep(0.5)  # Update every 0.5 seconds
                
        except KeyboardInterrupt:
            print("\n\n✓ Dashboard stopped")
    
    def check_errors(self):
        """Check for error codes and display them"""
        print("\n" + "="*60)
        print("       DIAGNOSTIC TROUBLE CODES (DTCs)")
        print("="*60)
        
        dtcs = self.read_dtcs()
        
        if len(dtcs) == 0:
            print("✓ No error codes found - System OK")
        else:
            print(f"⚠ Found {len(dtcs)} error code(s):\n")
            for dtc in dtcs:
                print(f"  • {dtc} - {self.get_dtc_description(dtc)}")
            
            # Ask to clear
            response = input("\nClear error codes? (y/n): ")
            if response.lower() == 'y':
                if self.clear_dtcs():
                    print("✓ Error codes cleared successfully")
                else:
                    print("✗ Failed to clear error codes")
        
        print("="*60 + "\n")
    
    def get_dtc_description(self, dtc_code):
        """Get human-readable description of DTC"""
        descriptions = {
            'P0133': 'O2 Sensor Circuit Slow Response',
            'P0171': 'System Too Lean (Bank 1)',
            'P0174': 'System Too Lean (Bank 2)',
            'P0300': 'Random/Multiple Cylinder Misfire',
            'P0301': 'Cylinder 1 Misfire Detected',
            'P0420': 'Catalyst System Efficiency Below Threshold',
            'P0440': 'EVAP System Malfunction',
            'P0562': 'System Voltage Low',
        }
        return descriptions.get(dtc_code, 'Unknown DTC')
    
    def close(self):
        """Close CAN bus connection and TCP socket"""
        self.tcp_socket.close()
        self.bus.shutdown()
        print("✓ Connection closed")


def main():
    """Main program entry point"""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║           OBD-II DIAGNOSTIC READER v1.0                   ║
║   Connects to ECU via CAN bus for vehicle diagnostics    ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Initialize OBD reader
    reader = OBDReader()
    
    # Menu
    while True:
        print("\nSelect option:")
        print("  1. Live Dashboard (Real-time sensor data)")
        print("  2. Check Error Codes (DTCs)")
        print("  3. Read Single Parameter")
        print("  4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            reader.display_dashboard()
        
        elif choice == '2':
            reader.check_errors()
        
        elif choice == '3':
            print("\nAvailable parameters:")
            print("  1. RPM")
            print("  2. Speed")
            print("  3. Coolant Temperature")
            print("  4. Throttle Position")
            print("  5. Engine Load")
            print("  6. Intake Air Temperature")
            
            param = input("Select parameter (1-6): ").strip()
            
            if param == '1':
                rpm = reader.read_rpm()
                if rpm is not None:
                    print(f"\n🔧 Engine RPM: {rpm:.0f} RPM")
                else:
                    print("\n⚠️  No response from ECU")
            elif param == '2':
                speed = reader.read_speed()
                if speed is not None:
                    print(f"\n🚗 Vehicle Speed: {speed:.0f} km/h")
                else:
                    print("\n⚠️  No response from ECU")
            elif param == '3':
                temp = reader.read_coolant_temp()
                if temp is not None:
                    print(f"\n🌡️  Coolant Temperature: {temp:.0f}°C")
                else:
                    print("\n⚠️  No response from ECU")
            elif param == '4':
                throttle = reader.read_throttle()
                if throttle is not None:
                    print(f"\n⚡ Throttle Position: {throttle:.1f}%")
                else:
                    print("\n⚠️  No response from ECU")
            elif param == '5':
                load = reader.read_engine_load()
                if load is not None:
                    print(f"\n📊 Engine Load: {load:.1f}%")
                else:
                    print("\n⚠️  No response from ECU")
            elif param == '6':
                intake = reader.read_intake_temp()
                if intake is not None:
                    print(f"\n🌡️  Intake Air Temperature: {intake:.0f}°C")
                else:
                    print("\n⚠️  No response from ECU")
        
        elif choice == '4':
            reader.close()
            print("\nGoodbye! 👋\n")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Program terminated by user")
        sys.exit(0)
