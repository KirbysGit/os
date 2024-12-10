# ---------------------------------------------
#                    Scheduler-gpt.py
#
# Description: This project prompts ChatGPT to
# implement a full scheduling algorithm that 
# works with FIFO, SJF, and RR and output
# metrics such as response time, turnaround
# time, and wait time. Along with outputing
# a detailed representation of the algorithm
# at each time step.
#
# Date Created: 9/14/2024
#
# Author: Jaxon Topel
#
# Team Members: 
#   - Colin Kirby
#   - Alex Beaufort
#   - Alex Downs
#   - Tylon Robinsons
#   - Jaxon Topel
#
# ---------------------------------------------

import sys
import os

# Define a Process class to store process information
class Process:
    def __init__(self, name, arrival, burst):
        self.name = name  # Process name
        self.arrival = arrival  # Arrival time of the process
        self.burst = burst  # Burst time (execution time) of the process
        self.remaining_time = burst  # Remaining burst time for the process
        self.wait_time = 0  # Wait time (calculated later)
        self.turnaround_time = 0  # Turnaround time (calculated later)
        self.response_time = None  # Response time, initialized as None
        self.start_time = None  # Start time, initialized as None

# Parse the input file for processes, algorithm type, and quantum (if RR)
def parse_input_file(input_file):
    with open(input_file, 'r') as file:
        lines = file.readlines()

    process_count = 0  # Number of processes
    run_for = 0  # Total runtime for the scheduler
    processes = []  # List of process objects
    algorithm = None  # Selected algorithm (fcfs, sjf, rr)
    quantum = None  # Time quantum (only used in RR)

    for line in lines:
        parts = line.split()

        if parts[0] == "processcount":
            process_count = int(parts[1])  # Read number of processes
        elif parts[0] == "runfor":
            run_for = int(parts[1])  # Read total runtime
        elif parts[0] == "use":
            algorithm = parts[1]  # Determine which algorithm to use
            if algorithm not in ["fcfs", "sjf", "rr"]:
                print(f"Error: Unsupported algorithm {algorithm}.")
                sys.exit(1)
        elif parts[0] == "quantum":
            # If Round Robin, read quantum, else throw error if quantum is present but not RR
            if algorithm == "rr":
                quantum = int(parts[1])
            else:
                print("Error: Quantum provided but algorithm is not round robin (rr).")
                sys.exit(1)
        elif parts[0] == "process":
            # Create a new Process object and append it to the process list
            name = parts[2]
            arrival = int(parts[4])
            burst = int(parts[6])
            processes.append(Process(name, arrival, burst))
        elif parts[0] == "end":
            break

    # Ensure quantum is provided for RR
    if algorithm == "rr" and quantum is None:
        print("Error: Missing quantum parameter when using round robin.")
        sys.exit(1)

    return process_count, run_for, processes, algorithm, quantum

# First-Come First-Served (FIFO) scheduler
def fifo_scheduler(processes, run_for):
    processes.sort(key=lambda x: x.arrival)  # Sort processes by arrival time
    current_time = 0  # Current time in the scheduler
    output_log = []  # Logs for output
    
    # Output the number of processes and the algorithm used
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using First-Come First-Served")

    arrived_processes = set()  # Keep track of processes that have been logged as arrived

    while current_time < run_for:
        # Log arrivals first, including those that arrived while CPU was busy
        for process in processes:
            if process.arrival <= current_time and process.name not in arrived_processes:
                output_log.append(f"Time {process.arrival:>3} : {process.name} arrived")
                arrived_processes.add(process.name)

        # Select the first process that has arrived and has not finished
        for process in processes:
            if process.arrival <= current_time and process.remaining_time > 0:
                # Process gets selected if it's the first time being selected
                if process.start_time is None:
                    process.start_time = current_time
                    process.response_time = current_time - process.arrival
                    output_log.append(f"Time {current_time:>3} : {process.name} selected (burst {process.burst:>3})")

                # Run the process for its burst time or until the scheduler run time ends
                time_to_run = min(process.remaining_time, run_for - current_time)

                # Log arrivals during the process execution
                for t in range(current_time + 1, current_time + time_to_run):
                    for proc in processes:
                        if proc.arrival == t and proc.name not in arrived_processes:
                            output_log.append(f"Time {t:>3} : {proc.name} arrived")
                            arrived_processes.add(proc.name)

                current_time += time_to_run  # Advance the time
                process.remaining_time -= time_to_run  # Decrease remaining time

                # If process finishes, log it and calculate turnaround and wait time
                if process.remaining_time == 0:
                    output_log.append(f"Time {current_time:>3} : {process.name} finished")
                    process.turnaround_time = current_time - process.arrival
                    process.wait_time = process.turnaround_time - process.burst
                break  # Break once a process is selected and run
        else:
            # If no process is ready to run, log idle time
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1

    # Collect final summary metrics
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in processes:
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {process.response_time:>3}"
        )

    return output_log

# Preemptive Shortest Job First (SJF) scheduler
def sjf_scheduler(processes, run_for):
    processes.sort(key=lambda x: x.arrival)  # Sort by arrival time initially
    current_time = 0  # Current time in the scheduler
    output_log = []  # Logs for output
    ready_queue = []  # Ready queue for processes
    arrived_processes = set()  # Track arrived processes
    selected_process = None  # Track currently selected process
    
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using preemptive Shortest Job First")
    
    while current_time < run_for:
        # Log arrivals at current time step
        arrivals_to_log = []
        for process in processes:
            if process.arrival == current_time and process.name not in arrived_processes:
                arrivals_to_log.append(process)
                ready_queue.append(process)
                arrived_processes.add(process.name)

        # Log the arrivals before processing selections
        for process in arrivals_to_log:
            output_log.append(f"Time {current_time:>3} : {process.name} arrived")
        
        # Sort the ready queue by remaining burst time (Shortest Job First)
        ready_queue.sort(key=lambda x: (x.remaining_time, x.arrival))

        # Select process with shortest remaining time
        if ready_queue:
            current_process = ready_queue[0]  # Get the process with the shortest remaining burst time
            
            # Log selection if it's newly selected or preempted
            if current_process != selected_process:
                if current_process.remaining_time == current_process.burst:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.burst:>3})")
                else:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.remaining_time:>3})")
                
                selected_process = current_process
            
            # Set response time if not already set
            if current_process.response_time is None:
                current_process.response_time = current_time - current_process.arrival

            # Run the process for one time unit
            current_process.remaining_time -= 1
            current_time += 1

            # If the process finishes, log it and remove from the ready queue
            if current_process.remaining_time == 0:
                output_log.append(f"Time {current_time:>3} : {current_process.name} finished")
                current_process.turnaround_time = current_time - current_process.arrival
                current_process.wait_time = current_process.turnaround_time - current_process.burst
                ready_queue.pop(0)  # Remove finished process
                selected_process = None  # Reset selected process
        else:
            # If no process is ready, log idle time
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1

    # Collect summary and final output
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in sorted(processes, key=lambda x: x.name):
        response_time = process.response_time if process.response_time is not None else 0
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {response_time:>3}"
        )

    return output_log

# Round-Robin (RR) scheduler
def rr_scheduler(processes, run_for, quantum):
    processes.sort(key=lambda x: x.arrival)  # Sort processes by arrival time
    current_time = 0  # Current time in the scheduler
    output_log = []  # Logs for output
    ready_queue = []  # Ready queue for processes
    arrived_processes = set()  # Track arrived processes

    # Output the number of processes and the algorithm used
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using Round-Robin")
    output_log.append(f"Quantum   {quantum}")
    output_log.append("")  # Add blank line after Quantum line

    while current_time < run_for:
        # Add any new arrivals to the ready queue
        for process in processes:
            if process.arrival <= current_time and process.name not in arrived_processes:
                output_log.append(f"Time {current_time:>3} : {process.name} arrived")
                ready_queue.append(process)
                arrived_processes.add(process.name)

        # Select and process a task from the ready queue
        if ready_queue:
            current_process = ready_queue.pop(0)  # Get the next process in the queue
            
            # Log the process selection and set response time if it's the first time being selected
            if current_process.start_time is None:
                current_process.start_time = current_time
                current_process.response_time = current_time - current_process.arrival
            output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.remaining_time:>3})")
            
            # Run the process for quantum or remaining burst time
            time_to_run = min(quantum, current_process.remaining_time)
            
            # Simulate running the process for the quantum
            for _ in range(time_to_run):
                current_process.remaining_time -= 1
                current_time += 1
                
                # Check for new arrivals during this time
                for process in processes:
                    if process.arrival == current_time and process.name not in arrived_processes:
                        output_log.append(f"Time {current_time:>3} : {process.name} arrived")
                        ready_queue.append(process)
                        arrived_processes.add(process.name)

                # If the process finishes, log it and break
                if current_process.remaining_time == 0:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} finished")
                    current_process.turnaround_time = current_time - current_process.arrival
                    current_process.wait_time = current_process.turnaround_time - current_process.burst
                    break
            else:
                # If the process didn't finish, add it back to the ready queue
                ready_queue.append(current_process)
        else:
            # If no process is ready, log idle time
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1

    # Collect summary metrics
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in processes:
        response_time = process.response_time if process.response_time is not None else 0
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {response_time:>3}"
        )

    return output_log

# Write the output to the actual folder
def write_output_file(output_file, output_log):
    with open(output_file, 'w') as file:
        for line in output_log:
            file.write(line + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: scheduler-gpt.py <input file>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not input_file.endswith(".in"):
        print("Error: Input file must have a .in extension.")
        sys.exit(1)

    # Ensure output file is written to the "actual" folder
    base_filename = os.path.basename(input_file).replace(".in", ".out")
    output_file = os.path.join("actual", base_filename)

    # Create 'actual' directory if it doesn't exist
    if not os.path.exists("actual"):
        os.makedirs("actual")

    # Parse the input file to get process count, run time, process list, and algorithm
    process_count, run_for, processes, algorithm, quantum = parse_input_file(input_file)

    # Decide which scheduling algorithm to run
    if algorithm == "fcfs":
        output_log = fifo_scheduler(processes, run_for)
    elif algorithm == "sjf":
        output_log = sjf_scheduler(processes, run_for)
    elif algorithm == "rr":
        output_log = rr_scheduler(processes, run_for, quantum)
    else:
        print(f"Error: Unsupported algorithm {algorithm}.")
        sys.exit(1)

    # Write the output to the corresponding file
    write_output_file(output_file, output_log)