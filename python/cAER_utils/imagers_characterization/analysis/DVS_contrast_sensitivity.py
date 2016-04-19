# ############################################################
# python class that deals with cAER aedat3 file format
# and calculates CONTRAST SENSITIVITY of DVS
# author  Federico Corradi - federico.corradi@inilabs.com
# author  Diederik Paul Moeys - diederikmoeys@live.com
# ############################################################
from __future__ import division
import os
import struct
import threading
import sys
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import string
from pylab import *
import scipy.stats as st
import math
import matplotlib as mpl
sys.path.append('utils/')
import load_files
import operator

class DVS_contrast_sensitivity:
    def cs_analysis(self, sensor, cs_dir, figure_dir, frame_y_divisions, frame_x_divisions, sine_freq = 1.0, num_oscillations = 100.0, single_pixels_analysis=False, rmse_reconstruction=False):
        '''
            Contrast sensitivity analisys and signal reconstruction
            Input signal is a sine wave from the integrating sphere
        '''
        # Initialize arrays    
        directory = cs_dir    
        files_in_dir = []
        file_n = 0
        files_in_dir_raw = os.listdir(directory)
        for this_file in range(len(files_in_dir_raw)):
            newpath = os.path.join(cs_dir,files_in_dir_raw[this_file])
            if(not os.path.isdir(newpath)): # Remove folders
                files_in_dir.append(files_in_dir_raw[this_file])
                file_n = file_n + 1
        files_in_dir.sort()  
        this_file = 0
        rmse_tot = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        contrast_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        base_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        rec_time = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        contrast_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        base_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        on_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        diff_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        off_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])     
        refss_level = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])    
        contrast_sensitivity_off_average_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        contrast_sensitivity_on_average_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        contrast_sensitivity_off_median_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        contrast_sensitivity_on_median_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        err_off_percent_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        err_on_percent_array = np.zeros([len(files_in_dir),len(frame_x_divisions),len(frame_y_divisions)])
        delta_on_tot = []
        delta_off_tot = []
        
        # Extract the parameters from the file name as well as all the data from the .aedat3 file
        for this_file in range(len(files_in_dir)):            
            print ""
            print "*************"            
            print "** File # " +str(this_file+1)+ "/" + str(len(files_in_dir))
            print "*************"            
            if not os.path.isdir(directory+files_in_dir[this_file]):
                print("Loading data..")    
                '''               
                REMEMBER:
                filename = folder + '/contrast_sensitivity_recording_time_'+format(int(recording_time), '07d')+\
                '_contrast_level_'+format(int(contrast_level*100),'03d')+\
                '_base_level_'+str(format(int(base_level),'03d'))+\
                '_on_'+str(format(int(onthr),'03d'))+\
                '_diff_'+str(format(int(diffthr),'03d'))+\
                '_off_'+str(format(int(offthr),'03d'))+\
                '_refss_'+str(format(int(refss),'03d'))+\
                '.aedat'
                '''
                this_rec_time = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[0]) # in us
                this_contrast = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[3])/100
                this_base_level = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[6])
                this_on_level = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[8])
                this_diff_level = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[10])
                this_off_level = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[12])
                if(sensor == 'DAVIS208Mono'):
                    this_refss_level = float(files_in_dir[this_file].strip(".aedat").strip("constrast_sensitivity_recording_time_").split("_")[14])
                               
                loader = load_files.load_files()
                [frame, xaddr, yaddr, pol, ts, sp_t, sp_type] = loader.load_file(directory+files_in_dir[this_file])
                print("Addresses extracted")
            else:
                print("Skipping path "+ str(directory+files_in_dir[this_file])+ " as it is a directory")
                continue

            fit_done = False
            ion()
            
            #### Prepare FPN
            if(single_pixels_analysis):
                #calculate normalization factor
                delta_on_count_max = 0
                delta_off_count_max = 0
                for this_div_x in range(len(frame_x_divisions)) :
                    for this_div_y in range(len(frame_y_divisions)):
                        # Prepare empty arrays
                        x_to_get = np.linspace(frame_x_divisions[this_div_x][0],frame_x_divisions[this_div_x][1]-1,frame_x_divisions[this_div_x][1]-frame_x_divisions[this_div_x][0])
                        y_to_get = np.linspace(frame_y_divisions[this_div_y][0],frame_y_divisions[this_div_y][1]-1,frame_y_divisions[this_div_y][1]-frame_y_divisions[this_div_y][0]) 
                        index_to_get, un = self.ismember(xaddr,x_to_get)
                        indey_to_get, un = self.ismember(yaddr,y_to_get)
                        final_index = (index_to_get & indey_to_get)
                        if(np.sum(final_index) > 0):
                            for x_ in range(frame_x_divisions[this_div_x][0],frame_x_divisions[this_div_x][1]):
                                for y_ in range(frame_y_divisions[this_div_y][0],frame_y_divisions[this_div_y][1]):
                                    this_index_x = xaddr[final_index] == x_
                                    this_index_y = yaddr[final_index] == y_
                                    index_to_get = this_index_x & this_index_y
                                    x_index = x_ - frame_x_divisions[this_div_x][0]
                                    y_index = y_ - frame_y_divisions[this_div_y][0]
                                    current_delta_on = np.sum(pol[final_index][index_to_get] == 1)
                                    current_delta_off = np.sum(pol[final_index][index_to_get] == 0)
                                    # Pixels with highest count of OFF or ON
                                    if( delta_off_count_max < current_delta_on):
                                        delta_off_count_max = current_delta_off
                                    if( delta_on_count_max < current_delta_off):
                                        delta_on_count_max  = current_delta_on
            ###                         
            
            
            # For every division in x and y at particular contrast and base level
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   
                    rec_time[this_file,this_div_x,this_div_y] = this_rec_time
                    contrast_level[this_file,this_div_x,this_div_y] = this_contrast
                    base_level[this_file,this_div_x,this_div_y] = this_base_level  
                    on_level[this_file,this_div_x,this_div_y] = this_on_level  
                    diff_level[this_file,this_div_x,this_div_y] = this_diff_level  
                    off_level[this_file,this_div_x,this_div_y] = this_off_level  
                    if(sensor == 'DAVIS208Mono'):
                        refss_level[this_file,this_div_x,this_div_y] = this_refss_level  
                    
                    print ""
                    print "####################################################################"
                    print "FILE: " + str(this_file+1) + "/" + str(len(files_in_dir)) + ", X: " + str(this_div_x+1) + "/" + str(len(frame_x_divisions)) + ", Y: " + str(this_div_y+1) + "/" + str(len(frame_y_divisions)) 
                    print "FILE NAME: " + files_in_dir[this_file]             
                    print "####################################################################"
                    
                    # Initialize parameters
                    signal_rec = []
                    tmp = 0
                    delta_on_average = 1.0
                    delta_off_average = 1.0
                    on_event_count_average_per_pixel = 0.0
                    off_event_count_average_per_pixel = 0.0
                    ts_t = []  
                    xaddr_ar = np.array(xaddr)
                    yaddr_ar = np.array(yaddr)
                    pol_ar = np.array(pol)
                    range_x = frame_x_divisions[this_div_x][1] - frame_x_divisions[this_div_x][0]
                    range_y = frame_y_divisions[this_div_y][1] - frame_y_divisions[this_div_y][0]
                    matrix_count_on = np.zeros([range_x,range_y])
                    matrix_count_off = np.zeros([range_x,range_y])
                    delta_matrix_off = np.ones([frame_x_divisions[this_div_x][1]-frame_x_divisions[this_div_x][0], frame_y_divisions[this_div_y][1]-frame_y_divisions[this_div_y][0]])
                    delta_matrix_on = np.ones([frame_x_divisions[this_div_x][1]-frame_x_divisions[this_div_x][0], frame_y_divisions[this_div_y][1]-frame_y_divisions[this_div_y][0]])  
                    
                    # Count spikes separately
                    print "Counting spikes.."
                    if(single_pixels_analysis):
                        for this_x in range(range_x):
                            for this_y in range(range_y):
                                index_x = xaddr_ar == this_x
                                index_y = yaddr_ar == this_y 
                                index_this_pixel = index_x & index_y    
                                num_on_spikes = np.sum(pol_ar[index_this_pixel] == 1)
                                num_off_spikes = np.sum(pol_ar[index_this_pixel] == 0)
                                matrix_count_on[this_x,this_y] = num_on_spikes
                                matrix_count_off[this_x,this_y] = num_off_spikes             
                    else:
                        for this_ev in range(len(ts)):
                            if (xaddr[this_ev] >= frame_x_divisions[this_div_x][0] and \
                                xaddr[this_ev] <= frame_x_divisions[this_div_x][1] and \
                                yaddr[this_ev] >= frame_y_divisions[this_div_y][0] and \
                                yaddr[this_ev] <= frame_y_divisions[this_div_y][1]):
                                if( pol[this_ev] == 1):
                                  on_event_count_average_per_pixel = on_event_count_average_per_pixel+1        
                                if( pol[this_ev] == 0):
                                  off_event_count_average_per_pixel = off_event_count_average_per_pixel+1
                        on_event_count_average_per_pixel = on_event_count_average_per_pixel/(num_oscillations*range_y*range_x)
                        off_event_count_average_per_pixel = off_event_count_average_per_pixel/(num_oscillations*range_y*range_x)
                    print("Events counted")
                    
                    # Plot spike counts
                    if(single_pixels_analysis):
                        fig= plt.figure()
                        ax = fig.add_subplot(121)
                        ax.set_title('Median ON/pix/cycle')
                        plt.xlabel ("X")
                        plt.ylabel ("Y")
                        im = plt.imshow(matrix_count_on, interpolation='nearest', origin='low', extent=[frame_x_divisions[this_div_x][0], frame_x_divisions[this_div_x][1], frame_y_divisions[this_div_y][0], frame_y_divisions[this_div_y][1]])
                        ax = fig.add_subplot(122)
                        ax.set_title('Median OFF/pix/cycle')
                        plt.xlabel ("X")
                        plt.ylabel ("Y")
                        im = plt.imshow(matrix_count_off, interpolation='nearest', origin='low', extent=[frame_x_divisions[this_div_x][0], frame_x_divisions[this_div_x][1], frame_y_divisions[this_div_y][0], frame_y_divisions[this_div_y][1]])
                        fig.tight_layout()                    
                        fig.subplots_adjust(right=0.8)
                        cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
                        fig.colorbar(im, cax=cbar_ax)     
                        plt.draw()
                        plt.savefig(figure_dir+"matrix_count_on_and_off_"+str(this_file)+"_Area_X_"+str(frame_x_divisions[this_div_x])+"_Y_"+str(frame_y_divisions[this_div_y])+".png",  format='png', dpi=300)
                        plt.savefig(figure_dir+"matrix_count_on_and_off_"+str(this_file)+"_Area_X_"+str(frame_x_divisions[this_div_x])+"_Y_"+str(frame_y_divisions[this_div_y])+".pdf",  format='pdf')
    
                        [dim1, dim2] = np.shape(matrix_count_on)
                        on_event_count_median_per_pixel = median(matrix_count_on)/(num_oscillations)
                        off_event_count_median_per_pixel = median(matrix_count_off)/(num_oscillations)
                        on_event_count_average_per_pixel = float(sum(matrix_count_on))/(dim1*dim2*num_oscillations)
                        off_event_count_average_per_pixel = float(sum(matrix_count_off))/(dim1*dim2*num_oscillations)
                        
                    print "Area: X: " + str(frame_x_divisions[this_div_x]) + ", Y: " + str(frame_y_divisions[this_div_y])
                    print "This contrast: " + str(this_contrast)
                    print "This oscillations: " + str(num_oscillations)
                    print "This recording time: " + str(this_rec_time)
                    print "This base level: " + str(this_base_level)
                    print "This on level: " + str(this_on_level)
                    print "This diff level: " + str(this_diff_level)
                    print "This off level: " + str(this_off_level)  
                    if(sensor == 'DAVIS208Mono'):
                        print "This refss level: " + str(this_refss_level) 
                    if(single_pixels_analysis):
                        print "Off median per pixel per cycle: " + str(off_event_count_median_per_pixel)
                        print "On median per pixel per cycle: " + str(on_event_count_median_per_pixel) 
                    print "Off average per pixel per cycle: " + str(off_event_count_average_per_pixel)
                    print "On average per pixel per cycle: " + str(on_event_count_average_per_pixel)
                    
                    # Plot histograms if Off and On counts
                    if(single_pixels_analysis):
                        fig= plt.figure()
                        ax = fig.add_subplot(121)
                        ax.set_title('ON/pix/cycle')
                        plt.xlabel ("ON per pixel per cycle")
                        plt.ylabel ("Count")
                        im = plt.hist(reshape(matrix_count_on, dim1*dim2)/(num_oscillations), 20)
                        ax = fig.add_subplot(122)
                        ax.set_title('OFF/pix/cycle')
                        plt.xlabel ("OFF per pixel per cycle")
                        plt.ylabel ("Count")
                        im = plt.hist(reshape(matrix_count_off, dim1*dim2)/(num_oscillations), 20)
                        fig.tight_layout()     
                        plt.savefig(figure_dir+"histogram_on_off_"+str(this_file)+"_Area_X_"+str(frame_x_divisions[this_div_x])+"_Y_"+str(frame_y_divisions[this_div_y])+".png",  format='png', dpi=300)
                        plt.savefig(figure_dir+"histogram_on_off_"+str(this_file)+"_Area_X_"+str(frame_x_divisions[this_div_x])+"_Y_"+str(frame_y_divisions[this_div_y])+".pdf",  format='pdf')
                        
                        # Confidence interval = error metric                    
                        err_off = self.confIntMean(reshape(matrix_count_off, dim1*dim2)/(num_oscillations))
                        err_on = self.confIntMean(reshape(matrix_count_on, dim1*dim2)/(num_oscillations))                    
                        print "Off confidence interval of 95%: " + str(err_off)
                        print "On confidence interval of 95%: " + str(err_on)
                        if(off_event_count_average_per_pixel != 0.0):
                            err_off_percent = 100*np.abs(err_off[0]-off_event_count_average_per_pixel)/off_event_count_average_per_pixel
                        else:
                            err_off_percent = np.nan
                        if(on_event_count_average_per_pixel != 0.0):                        
                            err_on_percent = 100*np.abs(err_on[0]-on_event_count_average_per_pixel)/on_event_count_average_per_pixel
                        else:
                            err_on_percent = np.nan
                        print "Off confidence interval of 95% within " + str('{0:.3f}'.format(err_off_percent))+ "% of mean"
                        print "On confidence interval of 95% within " + str('{0:.3f}'.format(err_on_percent))+ "% of mean"
                        err_off_percent_array [this_file,this_div_x,this_div_y] = err_off_percent
                        err_on_percent_array [this_file,this_div_x,this_div_y] = err_on_percent
                    
                    if(on_event_count_average_per_pixel == 0.0 and off_event_count_average_per_pixel == 0.0): # Not even ON or OFF!!
                        print "Not even a single spike.. skipping."
                        if(single_pixels_analysis):
                            delta_matrix_off = np.zeros([frame_x_divisions[this_div_x][1]-frame_x_divisions[this_div_x][0], frame_y_divisions[this_div_y][1]-frame_y_divisions[this_div_y][0]])
                            delta_matrix_on = np.zeros([frame_x_divisions[this_div_x][1]-frame_x_divisions[this_div_x][0], frame_y_divisions[this_div_y][1]-frame_y_divisions[this_div_y][0]])  
                            contrast_sensitivity_off_median_array[this_file,this_div_x,this_div_y] = np.nan
                            contrast_sensitivity_on_median_array[this_file,this_div_x,this_div_y] = np.nan
                        delta_off_average = 0.0
                        delta_on_average = 0.0
                        contrast_sensitivity_off_average_array[this_file,this_div_x,this_div_y] = np.nan
                        contrast_sensitivity_on_average_array[this_file,this_div_x,this_div_y] = np.nan
                        if(rmse_reconstruction):
                            rmse_tot[this_file,this_div_x, this_div_y] = np.nan
                    else:
                        # From the equation delta_on : on_event_count = delta_off_average : off_event_count (inverted to increase smaller eventcount's delta)
                        if(single_pixels_analysis):                           
                            ####
                            for x_ in range(frame_x_divisions[this_div_x][0],frame_x_divisions[this_div_x][1]):
                                for y_ in range(frame_y_divisions[this_div_y][0],frame_y_divisions[this_div_y][1]):
                                    tmp_rec = []
                                    tmp_t = []
                                    this_index_x = xaddr[final_index] == x_
                                    this_index_y = yaddr[final_index] == y_
                                    index_to_get = this_index_x & this_index_y
                                    
                                    x_index = x_ - frame_x_divisions[this_div_x][0]
                                    y_index = y_ - frame_y_divisions[this_div_y][0]
    
                                    if( matrix_count_on[x_index,y_index] > matrix_count_off[x_index,y_index]):
                                        if(delta_off_count_max != 0.0):
                                            delta_matrix_off[x_index,y_index] = (np.max(matrix_count_on) / double(delta_off_count_max)) * (delta_matrix_on[x_index,y_index])
                                        else:
                                            delta_matrix_off[x_index,y_index] = 0.0
                                    else:
                                        if(delta_on_count_max != 0.0):
                                            delta_matrix_on[x_index,y_index] = (np.max(matrix_count_off) / double(delta_on_count_max)) * (delta_matrix_off[x_index,y_index])
                                        else:
                                            delta_matrix_on[x_index,y_index] = 0.0
                            delta_on_tot.append(delta_matrix_on)
                            delta_off_tot.append(delta_matrix_off)
                            ########
                            
                        if(on_event_count_average_per_pixel > off_event_count_average_per_pixel): # to keep the max dlta to 1
                            if(off_event_count_average_per_pixel != 0.0):
                                delta_off_average = (double(on_event_count_average_per_pixel) / double(off_event_count_average_per_pixel)) * (delta_on_average)
                            else:
                                delta_off_average = 0.0 # made zero or reconstruction complains
                                if(single_pixels_analysis):
                                    off_event_count_median_per_pixel = np.nan # Make nan so that contrast sensitivity becomes nan (just a trick!)
                                off_event_count_average_per_pixel = np.nan
                        else:
                            if(on_event_count_average_per_pixel != 0.0):
                                delta_on_average = (double(off_event_count_average_per_pixel) / double(on_event_count_average_per_pixel)) * (delta_off_average)
                            else:
                                delta_on_average = 0.0
                                if(single_pixels_analysis):
                                    on_event_count_median_per_pixel = np.nan
                                on_event_count_average_per_pixel = np.nan
                        
                        # Get contrast sensitivity
                        # For 0.20 contrast / ((5 events on average per pixel) / 5 oscillations) = CS = 0.2
                        if(single_pixels_analysis):
                            contrast_sensitivity_on_median = (this_contrast)/(on_event_count_median_per_pixel)
                            contrast_sensitivity_off_median = (this_contrast)/(off_event_count_median_per_pixel)
                            contrast_sensitivity_off_median_array[this_file,this_div_x,this_div_y] = contrast_sensitivity_off_median
                            contrast_sensitivity_on_median_array[this_file,this_div_x,this_div_y] = contrast_sensitivity_on_median   
                            ttt = "CS off: "+str('%.3g'%(contrast_sensitivity_off_median))+" CS on: "+str('%.3g'%(contrast_sensitivity_on_median))

                        contrast_sensitivity_on_average = (this_contrast)/(on_event_count_average_per_pixel)
                        contrast_sensitivity_off_average = (this_contrast)/(off_event_count_average_per_pixel)                        
                        contrast_sensitivity_off_average_array[this_file,this_div_x,this_div_y] = contrast_sensitivity_off_average
                        contrast_sensitivity_on_average_array[this_file,this_div_x,this_div_y] = contrast_sensitivity_on_average
                        
                        # Reconstruct signal
                        if(rmse_reconstruction):
                            print "Reconstructing signal"
                            tmp = 0.0
                            for this_ev in range(len(ts)):
                                if (xaddr[this_ev] >= frame_x_divisions[this_div_x][0] and \
                                    xaddr[this_ev] <= frame_x_divisions[this_div_x][1] and \
                                    yaddr[this_ev] >= frame_y_divisions[this_div_y][0] and \
                                    yaddr[this_ev] <= frame_y_divisions[this_div_y][1]):
                                    if( pol[this_ev] == 1):
                                        tmp = tmp + delta_on_average
                                        signal_rec.append(tmp)
                                        ts_t.append(ts[this_ev])
                                    if( pol[this_ev] == 0):
                                        tmp = tmp - delta_off_average
                                        signal_rec.append(tmp)
                                        ts_t.append(ts[this_ev])
                                        
                        
                            if((not(not signal_rec)) and (len(signal_rec)>=5.0)): # More points than guess parameters are needed to get the fit to work
                                # Plot reconstructed signal
                                plt.figure()
                                ts = np.array(ts)
                                signal_rec = np.array(signal_rec)
                                signal_rec = signal_rec - np.mean(signal_rec) # Center signal at zero
                                amplitude_pk2pk_rec = np.abs(np.max(signal_rec)) + np.abs(np.min(signal_rec))
                                if(amplitude_pk2pk_rec == 0): # Hack to avoid problems
                                    amplitude_pk2pk_rec = 1
                                signal_rec = signal_rec/amplitude_pk2pk_rec # Normalize
                                # Initial guesses
                                guess_amplitude = np.max(signal_rec) - np.min(signal_rec)
                                offset_out = 7.0 # Outside log()
                                offset_in = 8.0 # Inside log()
                                p0=[sine_freq, guess_amplitude, 0.0, offset_in, offset_out]
                                signal_rec = signal_rec + 10 # Add offset of 10 to the reconstruction so there are no log(negative)                    
                                tnew = (ts_t-np.min(ts))*1e-6 # Restart timestamps
                                # Fit
                                try:
                                    fit = curve_fit(self.my_log_sin, tnew, signal_rec, p0=p0)
                                    data_fit = self.my_log_sin(tnew, *fit[0])
                                    rms = self.rms(signal_rec, data_fit) 
                                    fit_done = True
                                except RuntimeError:
                                    fit_done = False
                                    print "Not possible to fit, some error occurred"
                                if(fit_done and (math.isnan(rms) or math.isinf(rms))):
                                    fit_done = False
                                    print "We do not accept fit with NaN rmse"
        
                                data_first_guess = self.my_log_sin(tnew, *p0)
                                if fit_done:                  
                                    stringa = "- Fit - RMSE: " + str('{0:.3f}'.format(rms*100))+ "%"
                                    plt.plot(tnew, data_fit, label= stringa)
                                else:
                                    print "Fit failed, just plotting guess"
                                    rms = self.rms(signal_rec, data_first_guess)          
                                    stringa = "- Guess - RMSE: " + str('{0:.3f}'.format(rms*100))+ "%"
                                    plt.plot(tnew, data_first_guess, label=stringa)
                                if(single_pixels_analysis):
                                    plt.text(1, 11, ttt, ha='left')
                                rmse_tot[this_file,this_div_x, this_div_y] = rms
                                plt.plot(tnew, signal_rec, label='Reconstructed signal')
                                plt.legend(loc="lower right")
                                plt.xlabel('Time [s]')
                                plt.ylabel('Normalized Amplitude')
                                plt.ylim([8,12])
                                if fit_done:
                                    plt.title('Measured and fitted signal for the DVS pixels sinusoidal stimulation')
                                else:
                                    plt.title('Measured and guessed signal for the DVS pixels sinusoidal stimulation')
                                plt.savefig(figure_dir+"reconstruction_pixel_area_x"+str(frame_x_divisions[this_div_x][0])+"_"+str(frame_x_divisions[this_div_x][1])+"_"+str(this_file)+".pdf",  format='PDF')
                                plt.savefig(figure_dir+"reconstruction_pixel_area_x"+str(frame_x_divisions[this_div_x][0])+"_"+str(frame_x_divisions[this_div_x][1])+"_"+str(this_file)+".png",  format='PNG')
                                print(stringa)
                    
                    plt.close("all")   
                    print "Delta OFF: " + str(delta_off_average)
                    print "Delta ON: " + str(delta_on_average)
                    print "Contrast sensitivity off average: " + str('{0:.3f}'.format(contrast_sensitivity_off_average*100))+ "%"
                    print "Contrast sensitivity on average: " + str('{0:.3f}'.format(contrast_sensitivity_on_average*100))+ "%"
                    if(single_pixels_analysis):
                        print "Contrast sensitivity off median: " + str('{0:.3f}'.format(contrast_sensitivity_off_median*100))+ "%"
                        print "Contrast sensitivity on median: " + str('{0:.3f}'.format(contrast_sensitivity_on_median*100))+ "%"

        # Colors
        colors = cm.rainbow(np.linspace(0, 1, len(frame_x_divisions)*len(frame_y_divisions)*4))
        # Plots
        if(rmse_reconstruction):
            plt.figure()
            color_tmp = 0
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   plt.plot(100*contrast_level[:,this_div_x, this_div_y],rmse_tot[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.xlabel("Contrast level")
            plt.ylabel(" RMSE ")
            plt.savefig(figure_dir+"contrast_level_vs_rmse.pdf",  format='PDF')
            plt.savefig(figure_dir+"contrast_level_vs_rmse.png",  format='PNG')
        
            plt.figure()
            color_tmp = 0
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   plt.plot(rmse_tot[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='OFF - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1               
                   plt.plot(rmse_tot[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='ON - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
                   if(single_pixels_analysis):
                       plt.plot(rmse_tot[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                       color_tmp = color_tmp+1
                       plt.plot(rmse_tot[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                       color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.xlabel("RMSE")
            plt.ylabel("Contrast sensitivity")
#            plt.ylim((0,100))
            plt.savefig(figure_dir+"contrast_sensitivity_vs_rmse.pdf",  format='PDF')
            plt.savefig(figure_dir+"contrast_sensitivity_vs_rmse.png",  format='PNG')
        
        plt.figure()
        color_tmp = 0
        for this_div_x in range(len(frame_x_divisions)) :
            for this_div_y in range(len(frame_y_divisions)):
               plt.plot(base_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='OFF - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
               color_tmp = color_tmp+1               
               plt.plot(base_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='ON - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
               color_tmp = color_tmp+1
               if(single_pixels_analysis):
                   plt.plot(base_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
                   plt.plot(base_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
        lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.xlabel("Base level [Lux]")
        plt.ylabel("Contrast sensitivity")
#        plt.ylim((0,100))
        plt.savefig(figure_dir+"contrast_sensitivity_vs_base_level.pdf",  format='PDF')
        plt.savefig(figure_dir+"contrast_sensitivity_vs_base_level.png",  format='PNG')

        plt.figure()
        color_tmp = 0
        for this_div_x in range(len(frame_x_divisions)) :
            for this_div_y in range(len(frame_y_divisions)):
               plt.plot(off_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='OFF - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
               color_tmp = color_tmp+1               
               plt.plot(off_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='ON - X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
               color_tmp = color_tmp+1
               if(single_pixels_analysis):
                   plt.plot(off_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
                   plt.plot(off_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
        lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.xlabel("Off level [FineValue]")
        plt.ylabel("Contrast sensitivity")
#        plt.ylim((0,100))
        plt.savefig(figure_dir+"contrast_sensitivity_vs_off_level.pdf",  format='PDF')
        plt.savefig(figure_dir+"contrast_sensitivity_vs_off_level.png",  format='PNG')
        
        if(single_pixels_analysis):
            plt.figure()
            color_tmp = 0
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   plt.plot(100*contrast_sensitivity_off_average_array[:,this_div_x, this_div_y], err_off_percent_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.xlabel("OFF Contrast sensitivity")
#            plt.xlim((0,100))
            plt.ylabel("95% conf interval in percentage from mean")
            plt.savefig(figure_dir+"error_off_vs_off_contrast_sensitivity.pdf",  format='PDF')
            plt.savefig(figure_dir+"error_off_vs_off_contrast_sensitivity.png",  format='PNG')
    
            plt.figure()
            color_tmp = 0
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   plt.plot(100*contrast_sensitivity_on_average_array[:,this_div_x, this_div_y], err_on_percent_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.xlabel("ON Contrast sensitivity")
#            plt.xlim((0,100))
            plt.ylabel("95% conf interval in percentage from mean")
            plt.savefig(figure_dir+"error_on_vs_on_contrast_sensitivity.pdf",  format='PDF')
            plt.savefig(figure_dir+"error_on_vs_on_contrast_sensitivity.png",  format='PNG')
        
        if(sensor == 'DAVIS208Mono'):
            plt.figure()
            color_tmp = 0
            for this_div_x in range(len(frame_x_divisions)) :
                for this_div_y in range(len(frame_y_divisions)):
                   plt.plot(refss_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1                   
                   plt.plot(refss_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_average_array[:,this_div_x, this_div_y], 'o', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                   color_tmp = color_tmp+1
                   if(single_pixels_analysis):
                       plt.plot(refss_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_off_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                       color_tmp = color_tmp+1
                       plt.plot(refss_level[:,this_div_x, this_div_y], 100*contrast_sensitivity_on_median_array[:,this_div_x, this_div_y], 'x', color=colors[color_tmp], label='X: ' + str(frame_x_divisions[this_div_x]) + ', Y: ' + str(frame_y_divisions[this_div_y]) )
                       color_tmp = color_tmp+1
            lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            plt.xlabel("Refss level [FineValue]")
            plt.ylabel("Contrast sensitivity")
#            plt.ylim((0,100))
            plt.savefig(figure_dir+"contrast_sensitivity_vs_refss_level.pdf",  format='PDF')
            plt.savefig(figure_dir+"contrast_sensitivity_vs_refss_level.png",  format='PNG')
            
        # FPN plots
        if(single_pixels_analysis):######### CHECK -1! file axis average!
            sensor_on = np.zeros(frame_x_divisions[-1], frame_y_divisions[-1])
            sensor_off = np.zeros(frame_x_divisions[-1], frame_y_divisions[-1])
            current_x = 0
            current_y = 0
            for slice_num in range(len(delta_up_thr)):
                slice_dim_x, slice_dim_y = np.shape(delta_on_tot[slice_num])            
                sensor_on[current_x:slice_dim_x+current_x,current_y:slice_dim_y+current_y] = delta_on_tot[slice_num]
                sensor_off[current_x:slice_dim_x+current_x,current_y:slice_dim_y+current_y] = delta_off_tot[slice_num]
                current_x = slice_dim_x+current_x
                current_y = current_y 
            plt.figure()
            plt.subplot(3,2,1)
            plt.title("UP thresholds")
            plt.imshow(sensor_on)
            plt.colorbar()
            plt.subplot(3,2,2)
            plt.title("DN thresholds")          
            plt.imshow(sensor_off)
            plt.colorbar()
            plt.subplot(3,2,3)
            plt.plot(np.sum(sensor_on,axis=0), label='up dim'+str( len(np.sum(sensor_on,axis=0)) ))
            plt.legend(loc='best')    
            plt.xlim([0,frame_x_divisions[0]])
            plt.subplot(3,2,4)
            plt.plot(np.sum(sensor_off,axis=0), label='dn dim'+str( len(np.sum(sensor_off,axis=0)) ))
            plt.xlim([0,frame_x_divisions[0]])
            plt.legend(loc='best')    
            plt.subplot(3,2,5)
            plt.plot(np.sum(sensor_on,axis=1), label='up dim'+str( len(np.sum(sensor_on,axis=1)) ))
            plt.legend(loc='best')    
            plt.xlim([0,frame_x_divisions[-1]])
            plt.subplot(3,2,6)
            plt.plot(np.sum(sensor_off,axis=1), label='dn dim'+str( len(np.sum(sensor_off,axis=1)) ))
            plt.xlim([0,frame_x_divisions[-1]])  
            plt.legend(loc='best')    
            plt.savefig(figure_dir+"threshold_mismatch_map.pdf",  format='PDF')
            plt.savefig(figure_dir+"threshold_mismatch_map.png",  format='PNG')
            
        # Tell best parameters
        for this_div_x in range(len(frame_x_divisions)) :
            for this_div_y in range(len(frame_y_divisions)):
                print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'            
                print "Area: X: " + str(frame_x_divisions[this_div_x]) + ", Y: " + str(frame_y_divisions[this_div_y])
                area_contrast_on = contrast_sensitivity_on_average_array[:,this_div_x, this_div_y]
                min_index_on, min_value_on = min(enumerate(area_contrast_on), key=operator.itemgetter(1))
                print "BEST ON average CONTRAST SENSITIVITY "+ str('{0:.3f}'.format(contrast_sensitivity_on_average_array[min_index_on,this_div_x, this_div_y]*100))+ "% at:"
                print "This base level: " + str(base_level[min_index_on,this_div_x, this_div_y])
                print "This on level: " + str(on_level[min_index_on,this_div_x, this_div_y])
                print "This diff level: " + str(diff_level[min_index_on,this_div_x, this_div_y])
                print "This off level: " + str(off_level[min_index_on,this_div_x, this_div_y])  
                if(sensor == 'DAVIS208Mono'):
                    print "This refss level: " + str(refss_level[min_index_on,this_div_x, this_div_y])       
                
                area_contrast_off = contrast_sensitivity_off_average_array[:,this_div_x, this_div_y]
                min_index_off, min_value_off = min(enumerate(area_contrast_off), key=operator.itemgetter(1))
                print "BEST OFF average CONTRAST SENSITIVITY "+ str('{0:.3f}'.format(contrast_sensitivity_off_average_array[min_index_on,this_div_x, this_div_y]*100))+ "% at:"
                print "This base level: " + str(base_level[min_index_on,this_div_x, this_div_y])
                print "This on level: " + str(on_level[min_index_on,this_div_x, this_div_y])
                print "This diff level: " + str(diff_level[min_index_on,this_div_x, this_div_y])
                print "This off level: " + str(off_level[min_index_on,this_div_x, this_div_y])  
                if(sensor == 'DAVIS208Mono'):
                    print "This refss level: " + str(refss_level[min_index_on,this_div_x, this_div_y])  
            
        return rmse_tot, contrast_level, base_level, on_level, diff_level, off_level, refss_level, contrast_sensitivity_off_average_array, contrast_sensitivity_on_average_array, contrast_sensitivity_off_median_array, contrast_sensitivity_on_median_array, err_on_percent_array, err_off_percent_array, delta_on_tot, delta_off_tot
	
    def confIntMean(self, a, conf=0.95):
        mean, sem, m = np.mean(a), st.sem(a), st.t.ppf((1+conf)/2., len(a)-1)
        return mean - m*sem, mean + m*sem

    def rms(self, predictions, targets):
        return np.sqrt(np.mean((predictions-targets)**2))

    def ismember(self, a, b):
        '''
        as matlab: ismember
        '''
        # tf = np.in1d(a,b) # for newer versions of numpy
        tf = np.array([i in b for i in a])
        u = np.unique(a[tf])
        index = np.array([(np.where(b == i))[0][-1] if t else 0 for i,t in zip(a,tf)])
        return tf, index

    def my_log_sin(self, x, freq, amplitude, phase, offset_in, offset_out):# log(sine) wave to fit
        return np.log(-np.sin( 2*np.pi* x * freq + phase) * amplitude + offset_in ) + offset_out