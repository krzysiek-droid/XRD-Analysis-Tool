import numpy as np
import matplotlib.pyplot as plt
#from scipy.signal import find_peaks

# Load data from the uploaded file
data = np.loadtxt(
    fr"file.xy")  # Replace with the correct file path
x_data = data[:, 0]
y_data = data[:, 1]


def find_first_nan(array: np.array, reverse: bool = False):
    first_nan_index = None
    if reverse:
        for i, val in enumerate(array[::-1]):
            if np.isnan(val):
                first_nan_index = len(array) - i  # Korekta indeksu dla odwróconej tablicy
                break
        return array[first_nan_index:] if first_nan_index is not None else np.array([])
    else:
        for i, val in enumerate(array):
            if np.isnan(val):
                first_nan_index = i - 1
                break
        return array[:first_nan_index] if first_nan_index is not None else np.array([])


mean = np.mean(y_data)
print(f"mean -> {mean}")
# noise_threshold specifies the multiplier of the mean value that is used to cut the noise below mean * multiplier value
noise_threshold = 1
# peak id magnitude, specifies multiplier of the mean that is used to confirm whether peak is actual peak or just random
# distortion
peak_id_magnitude = 1.7

peaks_overlap_threshold = 0.65
print(f"settings: noise threshold: {noise_threshold}, peak_id_magnitude: {peak_id_magnitude}, peaks_overlap_threshold: "
      f"{peaks_overlap_threshold}")



hills = np.copy(y_data)
hills[hills < noise_threshold * mean] = np.nan
hills_test = np.copy(hills)

decreasing, increasing = False, False
window = [0]
window_size = 7

curr_max = 0
peaks_y, peaks_x = [], []
peaks = []
last_peak_end = 0
for i, y in enumerate(hills[:-window_size]):
    if not np.isnan(y) and y > peak_id_magnitude * mean:
        if y >= max(hills[i:i + window_size]):
            # current y-value is a peak (within window)
            curr_max = y

            # get left range of a peak
            peak_left = find_first_nan(hills[:i], True)
            if len(peak_left) == 0:
                # that means that this peak belongs to the previous one, which is not perfectly simmetrical
                s = find_first_nan(hills[i:])
                hills[i : i + len(s)] = np.nan
                continue
            peak_left_idx = i - len(peak_left)

            # get right range of a peak, depending on whether it is a isolated pick, or 2 picks intersecting eachother
            # identification by searching NaN values in successive data points
            x = int(1.0 * len(peak_left))
            if (i + x) >= len(hills):
                x = len(hills) - i - 1

            # Create a mask for the 'right' part
            mask = ~np.isnan(hills[i:])
            if np.isnan(hills[i + x]):
                # peak is isolated
                peak_right = find_first_nan(hills[i:])
                peak_end_idx = i + len(peak_right)
            elif np.mean(hills[i : i + x]) / y > peaks_overlap_threshold:
                # which means that this peak is more flat
                peak_right = find_first_nan(hills[i:])
                peak_end_idx = i + len(peak_right)
            else:
                # overlapping peaks
                print(f"Overlapping peak")
                peak_end = min(hills[i: i + x])
                peak_end_idx = i + np.where(hills[i: i + x] == peak_end)[0][0]
                peak_right = hills[i:peak_end_idx]

            # calculate symmetry axis of a peak
            peaks_x.append(i)

            print(f"peak found at -> {y} - degree: {x_data[i]}")
            peak = np.concatenate((peak_left, peak_right))
            peaks.append(peak)
            print(f"peak range: {x_data[peak_left_idx]} -- {x_data[peak_end_idx]}, max-> {max(peak)}\n")

            hills[peak_left_idx:peak_end_idx] = np.nan

# Plot the data
plt.figure(figsize=(10, 8))  # Adjusted figure size for layout optimization
plt.plot(x_data, y_data, label='Data', color='blue')

# Generate table data
peak_labels = [f'{i+1}' for i in range(len(peaks_x))]
peak_positions = [x_data[peak] for peak in peaks_x]

# Draw vertical lines and label them above the line
for i, peak in enumerate(peaks_x):
    plt.vlines(x=x_data[peak], ymin=min(y_data), ymax=max(y_data), color='gray', linestyle='--')
    plt.text(x_data[peak], max(y_data) * 1.01, peak_labels[i],  # slightly above the max y-value
             verticalalignment='bottom', horizontalalignment='center', color='red', fontsize=9)

# Add a table below the plot
table = plt.table(cellText=list(zip(peak_labels, [f'{pos:.2f}' for pos in peak_positions])),
                  colLabels=['Peak Number', '2Theta'],
                  loc='bottom', cellLoc='center', bbox=[0, -0.5, 1, 0.3])  # Adjust bbox to fit below the axis

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.5)  # Scale the table, making the rows taller

plt.title('XRD Data Plot')
plt.xlabel('2Theta')
plt.ylabel('Intensity')
plt.grid(True)
plt.subplots_adjust(bottom=0.3)  # Make room for the table
plt.show()