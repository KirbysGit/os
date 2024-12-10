# Makefile

CC = gcc
CFLAGS = -pthread -Wall -Wextra -std=c99
TARGET = chash

all: $(TARGET)

$(TARGET): chash.c
	$(CC) $(CFLAGS) -o $(TARGET) chash.c

clean:
	rm -f $(TARGET) output.txt
