"""Orion 290A+ pH Sensor Serial Driver

Colin Dietrich 2020
"""

import time
import atexit
import serial


class Orion290A:
    """Driver for Thermo Orion 290A+ ISE/pH/mV/ORP meter"""
    
    def __init__(self, serial_port, baudrate=1200):
        
        # serial class instance
        self.ser = serial.Serial(serial_port, baudrate, timeout=2)
        
        # register closing the serial port to prevent hardware hang
        atexit.register(self.ser.close)
        
        # define newline to MS windows definition
        self.newline = "\r\n"
        
        # these strings are sent by the meter on errors
        self.error_list = ["Improper", "Undefined", "DecodeError"]

        # clear serial buffers
        self.clear_buffers()
        
        # print debug statements
        self.verbose = False
        
    def close(self):
        """Close the serial port"""
        self.ser.close()
    
    def clear_buffers(self):
        """Clear the input and output serial buffers"""
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
    def byte_wrap(self, s):
        """Convert a string to bytes in UTF-8 encoding
        
        Parameters
        ----------
        s : str
        
        Returns
        -------
        bytes in UTF-8
        """
        return bytes("{}".format(s), 'utf-8')
    
    def clean_line(self, line):
        """Clean a line of data to send to the meter.  Converts
        to UTF-8 and strips whitespace.
        
        Parameters
        ----------
        line : str, one line of data
        Returns
        -------
        str, line cleaned if complete or "DecodeError" if failure
        """
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return "DecodeError"
        line = line.strip()
        return line
    
    def get_all_lines(self, delay=1):
        """Get all lines in the input serial buffer
        
        Parameters
        ----------
        delay : int, seconds to delay after each line read
        
        Returns
        -------
        list : cleaned lines of data
        """
        line_list = []
        while self.ser.in_waiting > 0:
            line = self.clean_line(self.ser.readline())
            if len(line) > 0:
                line_list.append(line)
            time.sleep(delay)
        return line_list
        
    def command(self, command_str, delay=1):
        """Send one command to the meter.  Slows down writes
        by breaking into individual characters.
        
        Parameters
        ----------
        command_str : str, command to send to pH meter
        delay : int, delay in seconds between command characters
        
        Returns
        -------
        list : all string lines of reponse
        """
        line_list = ["no collection"]
        while True:
            # break the string down to characters
            for s in command_str:
                time.sleep(delay)
                self.ser.write(self.byte_wrap(s))
                time.sleep(0.1) 
                
            # send a newline to execute
            self.ser.write(self.byte_wrap(self.newline))
            time.sleep(delay)
            
            # get all lines of response from the meter
            line_list = self.get_all_lines(delay=delay)
            
            # check the integrity of the response
            # TODO: with the per character sending, this might be redundant
            for line in line_list:
                for error in self.error_list:
                    if error in line:
                        print("ERROR", line)
                        continue
            break
        return line_list
        
    def login(self, delay=1):
        """Log into the meter remotely
        
        Parameters
        ----------
        delay : int, seconds delay between command sequence items
        
        Returns
        -------
        str, response string from pH meter
        """
        # prep the meter's serial console
        time.sleep(delay)
        self.ser.write(self.byte_wrap(self.newline))
        time.sleep(delay)
        self.ser.write(self.byte_wrap(self.newline))
        time.sleep(delay)
        
        # clear the computer's serial buffers
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(delay)
        
        # send the remote login command
        response = self.command("rem")
        return response
        
    def print_record(self, delay=2):
        """Get one measurement from the meter.
        
        Parameters
        ----------
        delay : int, seconds delay before issuing print command
        Returns
        -------
        str : response from pH meter
        """
        time.sleep(delay)
        response = self.command("pr")
        return response

    def parse_record(self, response):
        """Parse a 'pr' command response
        
        Parameters
        ----------
        response : str, response from pH meter
        
        Returns
        -------
        pH : str, pH reading
        mV : str, mV reading
        t  : str, temperature in C reading
        """
        pH = [r for r in response if 'pH' in r][0]
        mV_C = [r for r in response if 'mV' in r][0]
        pH = pH.split('=')[1]
        mV, t = mV_C.split(' ')
        return pH, mV, t
    
    def exit(self, delay=2):
        """Exit remote control
        
        Parameters
        ----------
        delay : int, delay around issuing command
        
        Returns
        -------
        str : response from pH meter
        """
        time.sleep(delay)
        response = self.command("exit")
        time.sleep(delay)
        return response
        
    def burst(self, n=10):
        """Collect a burst of data
        
        Parameters
        ----------
        n : int, number of bursts to execute
        
        Returns
        -------
        None, prints to terminal
        """
        r = self.login()
        if self.verbose:
            print('Orion290A.burst login >> ', r)
        for _n in range(10):
            pr = self.print_record()
            pH, mV, t = self.parse_record(pr)
            
            print(time.ctime(), _n, pH, mV, t)
        r = self.exit()
        if self.verbose:
            print('Orion290A.burst exit >> ', r)
        self.close()
