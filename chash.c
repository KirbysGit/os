//  ------------------------------------------------
//                    chash.c
// 
//  Description: This assignment involves creating
//  a concurrent hash table that allows multiple
//  threads to access and modify data safely. Our 
//  hash table uses a linked-list data structure and 
//  relies on locks to ensure out thread safety.
//
//  Key functions: 
//      (1) Insert: insert a new key value pair or 
//          update an existing one.
//      (2) Delete: Deletes a valid key value pair.
//      (3) Search: Searches for a key value pair.
//      (4) Print: Prints the entire has table.
// 
//  Date: 11/5/24 - 11/14/24
// 
//  Team Members: 
//    - Jaxon Topel
//    - Colin Kirby
//    - Alex Beaufort
//    - Alex Downs
//    - Tylon Robinson
// 
//  ------------------------------------------------


#define _XOPEN_SOURCE 700

// Includes.
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <pthread.h>
#include <sys/time.h>
#include <inttypes.h>

#define MAX_COMMANDS 100

// Define hasRecord Structure.
typedef struct hash_struct
{
    uint32_t hash;                 // 32-bit unsigned integer for the hash value
    char name[50];                 // Arbitrary string up to 50 characters long
    uint32_t salary;               // 32-bit unsigned integer for the annual salary
    struct hash_struct *next;      // Pointer to the next node in the list
} hashRecord;

// Define Command Structure.
typedef struct
{
    char command_type[10];         // Command types: insert, delete, search, print
    char name[50];                 // Name associated with the command
    uint32_t salary;               // Salary value for insert commands
} Command;

// Global Variables.
hashRecord *hash_table = NULL;     // Pointer to the hash table
pthread_rwlock_t lock;             // Read-write lock for the hash table
int lock_acquisitions = 0;         // Counter for lock acquisitions
int lock_releases = 0;             // Counter for lock releases

// Condition Variables & Mutex for Insert Condition.
pthread_mutex_t inserts_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t inserts_cond = PTHREAD_COND_INITIALIZER;
int inserts_done = 0;

// File Ptr for Output.
FILE *output_fp;

// Function for Current Timestamp.
uint64_t get_timestamp()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((uint64_t)tv.tv_sec * 1000000) + tv.tv_usec;
}

// Jenkins's one_at_a_time hash function.
uint32_t jenkins_one_at_a_time_hash(const char *key)
{
    size_t length = strlen(key);
    size_t i = 0;
    uint32_t hash = 0;
    while (i != length)
    {
        hash += key[i++];
        hash += hash << 10;
        hash ^= hash >> 6;
    }

    hash += hash << 3;
    hash ^= hash >> 11;
    hash += hash << 15;
    return hash;
}

// Create New Node for Hash Table.
hashRecord *create_node(const char *name, uint32_t salary)
{
    // Allocate Memory for New Node.
    hashRecord *node = (hashRecord *)malloc(sizeof(hashRecord));
    if (node == NULL)
    {
        perror("malloc");
        exit(1);
    }

    // Set The Node's Data.
    node->hash = jenkins_one_at_a_time_hash(name);
    strncpy(node->name, name, 50);
    node->salary = salary;
    node->next = NULL;

    return node;
}

// Insert Func.
void insert(const char *name, uint32_t salary)
{
    hashRecord *node = create_node(name, salary);

    // Insert Node into Linked List.
    if (hash_table == NULL || hash_table->hash > node->hash)
    {
        node->next = hash_table;
        hash_table = node;
    }
    else
    {
        hashRecord *current = hash_table;
        while (current->next != NULL && current->next->hash < node->hash)
        {
            current = current->next;
        }
        if (current->hash == node->hash && strcmp(current->name, name) == 0)
        {
            // Update Cur Node.
            current->salary = salary;
            free(node);
        }
        else
        {
            node->next = current->next;
            current->next = node;
        }
    }
}

// Delete Func.
void delete(const char *name)
{
    uint32_t hash = jenkins_one_at_a_time_hash(name);
    hashRecord *current = hash_table;
    hashRecord *prev = NULL;

    while (current != NULL && current->hash < hash)
    {
        prev = current;
        current = current->next;
    }

    if (current != NULL && strcmp(current->name, name) == 0)
    {
        if (prev == NULL)
        {
            hash_table = current->next;
        }
        else
        {
            prev->next = current->next;
        }
        free(current);
    }
}

// Search Func.
uint32_t search(const char *name)
{
    uint32_t hash = jenkins_one_at_a_time_hash(name);
    hashRecord *current = hash_table;

    while (current != NULL && current->hash < hash)
    {
        current = current->next;
    }

    if (current != NULL && strcmp(current->name, name) == 0)
    {
        return current->salary;
    }
    else
    {
        return 0;
    }
}

// Function to Print Hash Table Sorted.
void print_hash_table()
{
    hashRecord *current = hash_table;
    while (current != NULL)
    {
        fprintf(output_fp, "%u,%s,%u\n", current->hash, current->name, current->salary);
        current = current->next;
    }
}

// Thread Func to Process Commands.
void *thread_function(void *arg)
{
    Command *cmd = (Command *)arg;
    uint64_t timestamp;

    if (strcmp(cmd->command_type, "insert") == 0)
    {
        // Print Command Exc Message.
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",INSERT,%s,%u\n", timestamp, cmd->name, cmd->salary);

        // Acquire Write Lock.
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",WRITE LOCK ACQUIRED\n", timestamp);
        pthread_rwlock_wrlock(&lock);
        __sync_add_and_fetch(&lock_acquisitions, 1);

        // Perform Insert.
        insert(cmd->name, cmd->salary);

        // Release Write Lock.
        pthread_rwlock_unlock(&lock);
        __sync_add_and_fetch(&lock_releases, 1);
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",WRITE LOCK RELEASED\n", timestamp);
    }
    else if (strcmp(cmd->command_type, "delete") == 0)
    {
        // Wait Until Inserts are done.
        pthread_mutex_lock(&inserts_mutex);
        while (!inserts_done)
        {
            timestamp = get_timestamp();
            fprintf(output_fp, "%" PRIu64 ": WAITING ON INSERTS\n", timestamp);
            pthread_cond_wait(&inserts_cond, &inserts_mutex);
        }
        pthread_mutex_unlock(&inserts_mutex);

        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ": DELETE AWAKENED\n", timestamp);

        // Print Command Exc Message.
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",DELETE,%s\n", timestamp, cmd->name);

        // Acquire Write Lock.
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",WRITE LOCK ACQUIRED\n", timestamp);
        pthread_rwlock_wrlock(&lock);
        __sync_add_and_fetch(&lock_acquisitions, 1);

        // Perform Delete.
        delete(cmd->name);

        // Release Write Lock.
        pthread_rwlock_unlock(&lock);
        __sync_add_and_fetch(&lock_releases, 1);
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",WRITE LOCK RELEASED\n", timestamp);
    }
    else if (strcmp(cmd->command_type, "search") == 0)
    {
        // Wait Until Inserts Done.
        pthread_mutex_lock(&inserts_mutex);
        while (!inserts_done)
        {
            timestamp = get_timestamp();
            fprintf(output_fp, "%" PRIu64 ": WAITING ON INSERTS\n", timestamp);
            pthread_cond_wait(&inserts_cond, &inserts_mutex);
        }
        pthread_mutex_unlock(&inserts_mutex);

        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",SEARCH,%s\n", timestamp, cmd->name);

        // Acquire Read Lock.
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",READ LOCK ACQUIRED\n", timestamp);
        pthread_rwlock_rdlock(&lock);
        __sync_add_and_fetch(&lock_acquisitions, 1);

        // Perform Search.
        uint32_t salary = search(cmd->name);
        if (salary != 0)
        {
            fprintf(output_fp, "%u,%s,%u\n", jenkins_one_at_a_time_hash(cmd->name), cmd->name, salary);
        }
        else
        {
            fprintf(output_fp, "No Record Found\n");
        }

        // Release Read Lock.
        pthread_rwlock_unlock(&lock);
        __sync_add_and_fetch(&lock_releases, 1);
        timestamp = get_timestamp();
        fprintf(output_fp, "%" PRIu64 ",READ LOCK RELEASED\n", timestamp);
    }

    free(cmd);
    return NULL;
}

// Main.
int main()
{
    int num_threads;

    // Open the commands.txt file.
    FILE *fp = fopen("commands.txt", "r");
    if (fp == NULL)
    {
        perror("Error opening commands.txt");
        exit(1);
    }

    // Open the output.txt file.
    output_fp = fopen("output.txt", "w");
    if (output_fp == NULL)
    {
        perror("Error opening output.txt");
        exit(1);
    }

    // Initialize the Read-Write Lock.
    pthread_rwlock_init(&lock, NULL);

    // Read # of Threads.
    char line[256];
    fgets(line, sizeof(line), fp);
    sscanf(line, "threads,%d,0", &num_threads);
    fprintf(output_fp, "Running %d threads\n", num_threads);

    // Arrays for Threads & Commands.
    pthread_t threads[MAX_COMMANDS];
    Command *commands[MAX_COMMANDS];
    int thread_count = 0;
    int num_inserts = 0;

    // Parse Commands & Create Threads.
    while (fgets(line, sizeof(line), fp) != NULL)
    {
        // Remove Newline.
        line[strcspn(line, "\n")] = '\0';

        // Allocate Mem for Command.
        Command *cmd = (Command *)malloc(sizeof(Command));

        // Split Line into Tokens.
        char *token = strtok(line, ",");
        if (token == NULL)
        {
            free(cmd);
            continue;
        }

        // Store Command Type.
        strcpy(cmd->command_type, token);

        // Handle Diff Command Types.
        if (strcmp(cmd->command_type, "insert") == 0)
        {
            num_inserts++;
            token = strtok(NULL, ",");
            strcpy(cmd->name, token);

            token = strtok(NULL, ",");
            cmd->salary = atoi(token);
        }
        else if (strcmp(cmd->command_type, "delete") == 0 ||
                 strcmp(cmd->command_type, "search") == 0)
        {
            token = strtok(NULL, ",");
            strcpy(cmd->name, token);
            cmd->salary = 0;
        }
        else
        {
            // Invalid Command, Skip.
            free(cmd);
            continue;
        }

        // Store Command & Create Thread.
        commands[thread_count] = cmd;
        pthread_create(&threads[thread_count], NULL, thread_function, (void *)cmd);
        thread_count++;
    }

    fclose(fp);

    // Wait for All Insert Threads.
    for (int j = 0; j < thread_count; j++)
    {
        if (strcmp(commands[j]->command_type, "insert") == 0)
        {
            pthread_join(threads[j], NULL);
        }
    }

    // Set inserts_done & Signal Condition Variable.
    pthread_mutex_lock(&inserts_mutex);
    inserts_done = 1;
    pthread_cond_broadcast(&inserts_cond);
    pthread_mutex_unlock(&inserts_mutex);

    // Wait For Other Threads to Finish.
    for (int j = 0; j < thread_count; j++)
    {
        if (strcmp(commands[j]->command_type, "insert") != 0)
        {
            pthread_join(threads[j], NULL);
        }
    }

    // Print Lock Stats.
    fprintf(output_fp, "\nNumber of lock acquisitions: %d\n", lock_acquisitions);
    fprintf(output_fp, "Number of lock releases: %d\n", lock_releases);

    // Acquire Read Lock to Print Hash Table.
    pthread_rwlock_rdlock(&lock);
    __sync_add_and_fetch(&lock_acquisitions, 1);

    print_hash_table();

    pthread_rwlock_unlock(&lock);
    __sync_add_and_fetch(&lock_releases, 1);

    // Destroy read-write Lock.
    pthread_rwlock_destroy(&lock);

    // Close Output File.
    fclose(output_fp);

    return 0;
}
