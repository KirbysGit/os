import sys
import os

class Process:
    def __init__(self, name, arrival, burst):
        self.name = name
        self.arrival = arrival
        self.burst = burst
        self.remaining_time = burst
        self.wait_time = 0
        self.turnaround_time = 0
        self.response_time = None
        self.start_time = None

def parse_input_file(input_file):
    with open(input_file, 'r') as file:
        lines = file.readlines()

    process_count = 0
    run_for = 0
    processes = []
    algorithm = None
    quantum = None

    for line in lines:
        parts = line.split()

        if parts[0] == "processcount":
            process_count = int(parts[1])
        elif parts[0] == "runfor":
            run_for = int(parts[1])
        elif parts[0] == "use":
            algorithm = parts[1]
            if algorithm not in ["fcfs", "sjf", "rr"]:
                print(f"Error: Unsupported algorithm {algorithm}.")
                sys.exit(1)
        elif parts[0] == "quantum":
            if algorithm == "rr":
                quantum = int(parts[1])
            else:
                print("Error: Quantum provided but algorithm is not round robin (rr).")
                sys.exit(1)
        elif parts[0] == "process":
            name = parts[2]
            arrival = int(parts[4])
            burst = int(parts[6])
            processes.append(Process(name, arrival, burst))
            # Debugging statement for process input parsing
            #print(f"DEBUG: Process {name} added with arrival time {arrival} and burst {burst}")
        elif parts[0] == "end":
            break

    if algorithm == "rr" and quantum is None:
        print("Error: Missing quantum parameter when using round robin.")
        sys.exit(1)

    return process_count, run_for, processes, algorithm, quantum



def fifo_scheduler(processes, run_for):
    processes.sort(key=lambda x: x.arrival)  # Sort by arrival time
    current_time = 0
    output_log = []
    
    # Output the number of processes and the algorithm used
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using First-Come First-Served")

    arrived_processes = set()  # Keep track of processes that have already been logged as arrived

    while current_time < run_for:
        # Log arrivals first, including those that might have arrived while the CPU was busy
        for process in processes:
            if process.arrival <= current_time and process.name not in arrived_processes:
                output_log.append(f"Time {process.arrival:>3} : {process.name} arrived")
                arrived_processes.add(process.name)

        # Find the first process that has arrived and hasn't finished
        for process in processes:
            if process.arrival <= current_time and process.remaining_time > 0:
                if process.start_time is None:
                    process.start_time = current_time
                    process.response_time = current_time - process.arrival
                    output_log.append(f"Time {current_time:>3} : {process.name} selected (burst {process.burst:>3})")

                # Run the process for its burst time
                time_to_run = min(process.remaining_time, run_for - current_time)

                # Log any process arrivals that happen while this process runs
                for t in range(current_time + 1, current_time + time_to_run):
                    for proc in processes:
                        if proc.arrival == t and proc.name not in arrived_processes:
                            output_log.append(f"Time {t:>3} : {proc.name} arrived")
                            arrived_processes.add(proc.name)

                current_time += time_to_run
                process.remaining_time -= time_to_run

                if process.remaining_time == 0:
                    output_log.append(f"Time {current_time:>3} : {process.name} finished")
                    process.turnaround_time = current_time - process.arrival
                    process.wait_time = process.turnaround_time - process.burst
                break
        else:
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1

    # Collect summary metrics
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in processes:
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {process.response_time:>3}"
        )

    return output_log

def sjf_scheduler(processes, run_for):
    processes.sort(key=lambda x: x.arrival)  # Sort by arrival time initially
    current_time = 0
    output_log = []
    ready_queue = []
    arrived_processes = set()
    selected_process = None  # Track the currently selected process
    
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using preemptive Shortest Job First")
    
    while current_time < run_for:
        #print(f"\nDEBUG: Current time: {current_time}")

        # 1. **Log all arrivals first at the current time step**
        arrivals_to_log = []
        for process in processes:
            if process.arrival == current_time and process.name not in arrived_processes:
                arrivals_to_log.append(process)
                ready_queue.append(process)
                arrived_processes.add(process.name)

        # Ensure that **arrivals are logged before any process completion**
        for process in arrivals_to_log:
            output_log.append(f"Time {current_time:>3} : {process.name} arrived")
            #print(f"DEBUG: Arrival logged: {process.name} at time {current_time}")
        
        # 2. **Sort the ready queue by remaining burst time (shortest job first)**
        ready_queue.sort(key=lambda x: (x.remaining_time, x.arrival))
        #print(f"DEBUG: Ready queue: {[p.name for p in ready_queue]}")

        # 3. **After logging arrivals, handle process completions or selections**
        if ready_queue:
            current_process = ready_queue[0]  # Select the process with the shortest remaining burst time
            
            # Log process selection only if it's newly selected or preempted
            if current_process != selected_process:
                if current_process.remaining_time == current_process.burst:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.burst:>3})")
                    #print(f"DEBUG: Process {current_process.name} selected with full burst of {current_process.burst}")
                else:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.remaining_time:>3})")
                    #print(f"DEBUG: Process {current_process.name} selected with remaining burst of {current_process.remaining_time}")
                
                selected_process = current_process
            
            # **Set the response time when the process is first selected**:
            if current_process.response_time is None:
                current_process.response_time = current_time - current_process.arrival
                #print(f"DEBUG: Response time set for {current_process.name}: {current_process.response_time}")

            # Run the process for one time unit
            current_process.remaining_time -= 1
            current_time += 1
            #print(f"DEBUG: Process {current_process.name} ran for 1 unit, remaining burst: {current_process.remaining_time}")

            # If the process finishes, log it and remove from the queue
            if current_process.remaining_time == 0:
                output_log.append(f"Time {current_time:>3} : {current_process.name} finished")
                #print(f"DEBUG: Process {current_process.name} finished at time {current_time}")
                current_process.turnaround_time = current_time - current_process.arrival
                current_process.wait_time = current_process.turnaround_time - current_process.burst
                ready_queue.pop(0)  # Remove finished process
                selected_process = None  # Reset selected process
        else:
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1
            #print("DEBUG: CPU Idle")

    # **Sort and output the final summary by process name to maintain proper order**:
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in sorted(processes, key=lambda x: x.name):
        response_time = process.response_time if process.response_time is not None else 0
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {response_time:>3}"
        )
        #print(f"DEBUG: Summary for {process.name}: wait {process.wait_time}, turnaround {process.turnaround_time}, response {response_time}")

    return output_log


def rr_scheduler(processes, run_for, quantum):
    processes.sort(key=lambda x: x.arrival)  # Sort by arrival time initially
    current_time = 0
    output_log = []
    ready_queue = []
    arrived_processes = set()

    # Output the number of processes and algorithm used
    output_log.append(f"  {len(processes)} processes")
    output_log.append(f"Using Round-Robin")
    output_log.append(f"Quantum   {quantum}")
    output_log.append("")  # Adding the extra space after Quantum line

    while current_time < run_for:
        # Add any new arrivals to the ready queue
        for process in processes:
            if process.arrival <= current_time and process.name not in arrived_processes:
                output_log.append(f"Time {current_time:>3} : {process.name} arrived")
                ready_queue.append(process)
                arrived_processes.add(process.name)

        # Debug: Display the ready queue after arrivals
        #print(f"DEBUG: Ready queue at time {current_time}: {[p.name for p in ready_queue]}")

        if ready_queue:
            # Select the first process in the queue
            current_process = ready_queue.pop(0)
            
            # Log the process selection and set response time if it's the first time being selected
            if current_process.start_time is None:
                current_process.start_time = current_time
                current_process.response_time = current_time - current_process.arrival
            output_log.append(f"Time {current_time:>3} : {current_process.name} selected (burst {current_process.remaining_time:>3})")
            
            # Run the process for the quantum or remaining burst time, whichever is smaller, but update time in steps
            time_to_run = min(quantum, current_process.remaining_time)
            
            for _ in range(time_to_run):
                # Increment time unit by unit, checking for new arrivals
                current_process.remaining_time -= 1
                current_time += 1
                
                # Add any new arrivals that happen during the quantum
                for process in processes:
                    if process.arrival == current_time and process.name not in arrived_processes:
                        output_log.append(f"Time {current_time:>3} : {process.name} arrived")
                        ready_queue.append(process)
                        arrived_processes.add(process.name)

                # If the process finishes before its full quantum, log it and break early
                if current_process.remaining_time == 0:
                    output_log.append(f"Time {current_time:>3} : {current_process.name} finished")
                    current_process.turnaround_time = current_time - current_process.arrival
                    current_process.wait_time = current_process.turnaround_time - current_process.burst
                    break
            else:
                # If the process didn't finish, add it back to the ready queue
                ready_queue.append(current_process)
        else:
            # No process to run, idle
            output_log.append(f"Time {current_time:>3} : Idle")
            current_time += 1

    # Collect summary metrics
    output_log.append(f"Finished at time {run_for:>3}")
    output_log.append("")
    for process in processes:
        # Handle the case where response_time is None by setting it to 0
        response_time = process.response_time if process.response_time is not None else 0
        output_log.append(
            f"{process.name} wait {process.wait_time:>3} turnaround {process.turnaround_time:>3} response {response_time:>3}"
        )

    return output_log


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

