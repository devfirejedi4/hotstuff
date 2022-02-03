from mpi4py import MPI

comm = MPI.COMM_WORLD
nprocs = comm.Get_size()
rank = comm.Get_rank()

# define constants
ROWS = 320
COLS = 480
NUM_PROCS = nprocs
ITERATIONS = 100

# helper function to find maximum temp diff for a sub-region
def find_max_diff(max_diff, old_element, new_element):
    diff = abs(new_element - old_element)
    if max_diff < diff:
        return diff
    return max_diff

# update a sub-region given adjacent elements
def update_region(max_row, max_col, part, rank, ghosts):
    max_diff = 0
    new_part = []
    left = ghosts[0]
    right = ghosts[1]
    for row in range(0, max_row):
        new_part.append([])
        for col in range(0, max_col):
            # if at the top-most, left-most, bottom-most, or right-most edge, then set value to 1.0
            if row == 0 or row == max_row - 1:
                new_part[row].append(1.0)
            elif col == 0 and rank == 0:
                new_part[row].append(1.0)
            elif col == max_col - 1 and rank == NUM_PROCS - 1:
                new_part[row].append(1.0)
            # else calculate the values
            else:
                # if left edge, get left ghost elements
                if col - 1 < 0:
                    old_element = part[row][col]
                    new_part[row].append((part[row - 1][col] + part[row + 1][col] + left[row] + part[row][col + 1]) / 4)
                    new_element = new_part[row][col]
                    max_diff = find_max_diff(max_diff, old_element, new_element)
                # else if right edge, get right ghost elements
                elif col + 1 > max_col - 1:
                    old_element = part[row][col]
                    new_part[row].append((part[row - 1][col] + part[row + 1][col] + part[row][col - 1] + right[row]) / 4)
                    new_element = new_part[row][col]
                    max_diff = find_max_diff(max_diff, old_element, new_element)
                # else in the middle
                else:
                    old_element = part[row][col]
                    new_part[row].append((part[row - 1][col] + part[row + 1][col] + part[row][col - 1] + part[row][col + 1]) / 4)
                    new_element = new_part[row][col]
                    max_diff = find_max_diff(max_diff, old_element, new_element)
    return [new_part, max_diff]

if __name__ == "__main__":
    # initialize a region
    region = []

    # populate region with initial vals
    for row in range(0, ROWS):
        region.append([])
        for col in range(0, COLS):
            # top: row == 0
            # bottom: row == ROWS-1
            # left: col == 0
            # right: col == COLS-1
            if row == 0 or row == ROWS - 1 or col == 0 or col == COLS - 1:
                region[row].append(1.0)
            else:
                region[row].append(0.0)

    # cut region into partitions
    # assumption: number of processes is evenly divisible by total number of columns
    # to make things simple: only creating partitions by cutting region vertically
    max_row = ROWS  # each partition has the same number of rows as the entire region (not splitting horizontally)
    max_col = int(COLS / NUM_PROCS)  # splitting region vertically
    list_of_parts = []
    for r in range(0, ROWS, max_row):
        for c in range(0, COLS, max_col):
            new_partition = []
            for row in range(r, max_row):
                new_partition.append([])
                for col in range(c, c + max_col):
                    new_partition[row].append(region[row][col])
            list_of_parts.append(new_partition)

    # process 0 (rank 0) is the main process
    if rank == 0:
        # process 0's sub-region is the first list in the list of partitions
        my_part = list_of_parts[0]

        # distribute the other sub-regions (partitions) to the other processes
        for i in range(1, len(list_of_parts)):
            part = list_of_parts[i]
            comm.send(part, dest=i, tag=11)

        # begin the iterative process
        t = 0
        while t < ITERATIONS:
            # figure out the ghost elements
            ghost_elements = []
            # for process 0 (the left-most sub-region), the ghost elements will be the last column of the sub-region
            for row in range(len(my_part)):
                ghost_elements.append(my_part[row][max_col - 1])
            # send ghost elements to process 2
            comm.send(ghost_elements, dest=1, tag=22)
            # ghost elements to the right sent by right process
            recv_ghost = comm.recv(source=1, tag=22)
            # after receiving ghost elements from process 2, update sub-region values and find max temp diff
            [my_part, max_diff] = update_region(max_row, max_col, my_part, rank, [[], recv_ghost])
            # wait to hear "done" message from all processes and store max diff values in a list
            done_msgs = [max_diff]
            while len(done_msgs) < NUM_PROCS:
                for d in range(1, NUM_PROCS):
                    recv_done = comm.recv(source=d, tag=33)
                    done_msgs.append(recv_done)
            # print shit
            if t % 5 == 0:
                print("timestamp:", t)
                print("max update diff:", done_msgs)
            t = t + 1
    # all other processes will do their thing
    else:
        for p in range(1, NUM_PROCS):
            if rank == p:
                # get sub-region partition
                my_part = comm.recv(source=0, tag=11)

                t = 0
                # begin iterative process
                while t < ITERATIONS:
                    # if right-most sub-region, ghost elements will be on the left edge
                    if p == NUM_PROCS - 1:
                        ghost_elements = []
                        for row in range(len(my_part)):
                            ghost_elements.append(my_part[row][0])
                        # send ghost elements to left process
                        comm.send(ghost_elements, dest=p-1, tag=22)
                        # ghost elements to the left sent by left process
                        recv_ghost = comm.recv(source=p-1, tag=22)
                        # after receiving ghost elements from process 2, update sub-region values and find max temp diff
                        [my_part, max_diff] = update_region(max_row, max_col, my_part, rank, [recv_ghost, []])
                        # send "done" message with max temp diff to 0
                        comm.send(max_diff, dest=0, tag=33)
                    # sandwiched sub-regions
                    else:
                        # will have left and right ghost elements
                        left_ghost_elements = []
                        right_ghost_elements = []
                        for row in range(len(my_part)):
                            left_ghost_elements.append(my_part[row][0])
                            right_ghost_elements.append(my_part[row][max_col - 1])
                        # send ghost elements to neighboring processes
                        comm.send(left_ghost_elements, dest=p-1, tag=22)
                        comm.send(right_ghost_elements, dest=p+1, tag=22)
                        # ghost elements to the left sent by left process
                        recv_ghost_left = comm.recv(source=p-1, tag=22)
                        # ghost elements to the right sent by right process
                        recv_ghost_right = comm.recv(source=p+1, tag=22)
                        # after receiving ghost elements from process 2, update sub-region values and find max temp diff
                        [my_part, max_diff] = update_region(max_row, max_col, my_part, rank, [recv_ghost_left, recv_ghost_right])
                        # send "done" message with max temp diff to 0
                        comm.send(max_diff, dest=0, tag=33)
                    t = t + 1
