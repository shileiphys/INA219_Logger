# Copyright (c) 2017 Adafruit Industries
# Author: Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

# Modified by Lei Shi to use two INA219 together as a current-logging device.

import os
import sys
import time
import datetime
import subprocess

import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219

DISPLAY_ENABLED = True
Logging_ENABLED = True

def get_hours_passed(time_delta):
    days = time_delta.days
    hours = time_delta.seconds / 3600.00

    hours_passed = days*24 + hours

    return (hours_passed)


def config_ina219(ina219):
    # optional : change configuration to use 32 samples averaging for both bus voltage and shunt voltage
    ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
    ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
    # optional : change voltage range to 16V
    ina219.bus_voltage_range = BusVoltageRange.RANGE_16V

    return ina219


def read_ina_2(ina1, ina2):
    v1, i1, v2, i2 = (-99,-99, -99, -99)

    try:
        v1 = ina1.bus_voltage + ina2.shunt_voltage
        i1 = ina1.current

        v2 = ina2.bus_voltage + ina2.shunt_voltage
        i2 = ina2.current

    except DeviceRangeError as e:
        print(e)

    return (v1,i1, v2,i2)


def main():

    global DISPLAY_ENABLED
    global Logging_ENABLED

    # Create the I2C interface.
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the SSD1306 OLED class.
    # The first two parameters are the pixel width and pixel height.
    # Change these to the right size for your display!
    try:
        disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
    except:
        print("Searching SSD1306 Display ... Failed!\n")
        DISPLAY_ENABLED = False

    if (DISPLAY_ENABLED):
        print("Display ... Enabled\n")

        # Clear display.
        disp.fill(0)
        disp.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        width = disp.width
        height = disp.height
        image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = -2
        top = padding
        bottom = height - padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0

        # Load default font.
        font = ImageFont.load_default()

        # Alternativly load TTF font. Make sure the .ttf font file is in the
        # same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php
        # font = ImageFont.truetype('/user/share/fonts/truetype/dejavu/DejaVuSans.ttf', g)

        # Draw a black Filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d\' \' -f1" ## cut -d' ' -f1
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        draw.text((x, top+0), "IP: "+IP, font=font, fill=255)

        # Display image.
        disp.image(image)
        disp.show()


    ina219_1 = INA219(i2c_bus=i2c, addr=0x40)
    ina219_1 = config_ina219(ina219_1)

    ina219_2 = INA219(i2c_bus=i2c, addr=0x41)
    config_ina219(ina219_2)

    # display some of the advanced field (just to test)
    print("INA219 Config Register:")
    print("  bus_voltage_range:    0x%1X" % ina219_1.bus_voltage_range)
    print("  gain:                 0x%1X" % ina219_1.gain)
    print("  bus_adc_resolution:   0x%1X" % ina219_1.bus_adc_resolution)
    print("  shunt_adc_resolution: 0x%1X" % ina219_1.shunt_adc_resolution)
    print("  mode:                 0x%1X" % ina219_1.mode)
    print("")


    try:
        duration = 0.01  # arg[1] sample duration in hours -- (36s)
        dly = 1         # arg[2] sample timer interval in seconds -- (10s)

        if (len(sys.argv) == 3):
            Logging_ENABLED = True
            print('Logging ... Enalbed')

            if ((float(sys.argv[1]) < 48) and (float(sys.argv[1]) > 0)): # maximum 48 hours
                duration = float(sys.argv[1])
            if ((int(sys.argv[2]) < 100) and (int(sys.argv[2]) > 0)):
                dly = int(sys.argv[2])
            print('Sample duration: %.3f hours, interval: %02d seconds'%(duration, dly))

            wdir = './log'
            if (os.path.exists(wdir)):
                print("Log folder exists")
            else:
                os.mkdir(wdir)
        else:
            Logging_ENABLED = False
            print('Logging ... Disabled!')

        print("")

        count = 0
        fidx = 1

        t0 = datetime.datetime.now()

        if (Logging_ENABLED):
            fn = t0.strftime("%Y-%m%d-%H%M") + '-%ds.log'%dly
            f = open(wdir+'/'+fn, 'w')

        print('--------------------------------------')
        print('ina1  V      mA      | ina2  V      mA')
        print('--------------------------------------')

        while (1):
            # check sample time
            t1 = datetime.datetime.now()
            dt = t1 - t0
            hours_passed = get_hours_passed(dt)

            # s = dt.total_seconds()
            # elapsed_time = '{:02}:{:02}:{:02}'.format(s // 3600, s % 3600 // 60, s % 60)
            elapsed_time = str(dt).split('.')[0]

            if (Logging_ENABLED and (hours_passed > duration)):
                break;

            if (Logging_ENABLED and (count != 0 and count % 500 == 0)):
                # close current file first
                f.close()

                fidx += 1
                t  = datetime.datetime.now()
                fn = t.strftime("%Y-%m%d-%H%M") + '-%ds.log'%dly
                f  = open(wdir+'/'+fn, 'w')

            count += 1

            v1, i1, v2, i2 = read_ina_2(ina219_1, ina219_2)

            if (Logging_ENABLED):
                f.write('%0.3f,%0.3f,%0.3f,%0.3f\n'%(v1,i1,v2,i2))

            test1 = '0x{0:x}: {1:0.3f}V {2:0.3f}mA'.format(ina219_1.i2c_addr, v1, i1)
            test2 = '0x{0:x}: {1:0.3f}V {2:0.3f}mA'.format(ina219_2.i2c_addr, v2, i2)
            print(test1 + '|' + test2)
            # print('0x{0:x}: {1:0.3f}V {2:0.3f}mA | 0x{3:x}: {4:0.3f}V {5:0.3f}mA'.format(
            #     ina219_1.i2c_addr, v1, i1, ina219_2.i2c_addr, v2, i2))

            if (DISPLAY_ENABLED):
                # Draw a black Filled box to clear the image.
                draw.rectangle((0, top+9, width, height-(top+9)), outline=0, fill=0)

                # draw.text((x, top+8), 'Elapsed T: %.1f (m)'%(hours_passed*60), font=font, fill=255)
                draw.text((x, top+8), 'Elapsed: '+ elapsed_time, font=font, fill=255)
                draw.text((x, top+16), test1, font=font, fill=255)
                draw.text((x, top+25), test2, font=font, fill=255)

                disp.image(image)
                disp.show()

            time.sleep(dly)

        if (Logging_ENABLED and (not f.closed)):
            f.close()

    except KeyboardInterrupt:
        print ("\nCtrl-C pressed.  Program exiting...")

    finally:
        pass


if __name__ == '__main__':
    main()
