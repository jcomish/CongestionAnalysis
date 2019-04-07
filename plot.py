import csv
import matplotlib.pyplot as plt
import pandas as pd
from os import listdir
from os.path import isfile, join


def parse_bandwidth_stream_logs(data, start_time=0.0):
    ret_data = []
    for row in data:
        trimmed_data = row[7:-1].replace("- ", "-")
        row = trimmed_data.split(" ")
        ret_data.append((float(row[0].split("-")[1]) + start_time, float(row[3])))

    return ret_data


def read_bandwidth_data(filename):
    file1 = open("modlogs/" + filename + "ms1.modlog", "r").readlines()[7:-1]
    file2 = open("modlogs/" + filename + "ms2.modlog", "r").readlines()[7:-1]

    return parse_bandwidth_stream_logs(file1), parse_bandwidth_stream_logs(file2, start_time=250.0)


def read_file_data(path):
    with open(path, "rt", encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ')
        cwnd1 = []
        cwnd2 = []
        for row in reader:
            try:
                if "10.0.0.1" in row[2]:
                    cwnd1.append((float(row[0]), float(row[6])))
                elif "10.0.0.2" in row[2]:
                    cwnd2.append((float(row[0]), float(row[6])))
            except:
                pass
    return cwnd1, cwnd2


def plot_bw_data(filename, plt):
    stream1, stream2 = read_bandwidth_data(filename)

    stream1 = pd.DataFrame(stream1, columns=['time', 'Bandwidth1'])
    stream2 = pd.DataFrame(stream2, columns=['time', 'Bandwidth2'])

    plt.set_title(filename + " Bandwidth Over Time (MB/second)")

    x1 = stream1['time']
    y1 = stream1['Bandwidth1']

    x2 = stream2['time']
    y2 = stream2['Bandwidth2']

    plt.plot(x1, y1, 'r')
    plt.plot(x2, y2, 'b')
    plt.legend(loc='upper left')
    return plt
    # plt.savefig("fairness/" + filename + ".png")


def plot_cwnd_graph(filename, plt):
    cwnd1, cwnd2 = read_file_data("logs/" + filename + ".log")
    cwnd1 = pd.DataFrame(cwnd1, columns=['time', 'cwnd1'])
    cwnd2 = pd.DataFrame(cwnd2, columns=['time', 'cwnd2'])

    # plt.figure()
    plt.set_title(filename[:-2] + " CWND Over Time (packets/second)")

    x1 = cwnd1['time']
    y1 = cwnd1['cwnd1']

    x2 = cwnd2['time']
    y2 = cwnd2['cwnd2']

    plt.plot(x1, y1, 'r')
    plt.plot(x2, y2, 'b')
    plt.legend(loc='upper left')
    return plt
    # plt.savefig("img/" + filename + ".png")


# for file in [f for f in listdir("logs") if isfile(join("logs", f))]:
#     plot_cwnd_graph(file[:-4])

list_of_files = [f for f in listdir("logs") if isfile(join("logs", f))]
set_of_files = set(list_of_files)

for file in set_of_files:
    print(file[:-6])
    f, axarr = plt.subplots(2, sharex=True)

    cwnd_graph = plot_cwnd_graph(file[:-4], axarr[0])
    bw_graph = plot_bw_data(file[:-6], axarr[1])

    # plt.show()
    plt.savefig("img/" + file[:-6] + ".png")
