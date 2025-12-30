import pandas as pd  # type: ignore
import numpy as np # type: ignore
from numpy.typing import NDArray # type: ignore
from typing import Any # type: ignore
from time import time # type: ignore
#from icecream import ic # type: ignore

class combine_crop_rows_from_connections:
    def __init__(self):
        self.connected_crop_rows = np.empty([0,12])
        self.crop_row_index = 0
        self.connecting_full = 0
        self.connections = 0
        self.time_connect_full = 0


    def connect_crop_rows_of_2_tiles(self, tile_1_number: int, tile_2_number: int, connections: NDArray[Any]) -> None:
        """
        Connect the crop rows of 2 tiles based on the connections
        The rows are connected to existing rows if any, otherwise new rows are added
        """
        for row in connections:
            unknown_crop_row = True
            
            # Find the index of the row if they where already added
            index_row_1 = np.array((self.connected_crop_rows[:, np.r_[1,2]] == (tile_1_number, row[0])).all(axis=1).nonzero()).reshape(-1)
            index_row_2 = np.array((self.connected_crop_rows[:, np.r_[1,2]] == (tile_2_number, row[1])).all(axis=1).nonzero()).reshape(-1)

            if index_row_1.size > 0 and index_row_2.size > 0:
                if self.connected_crop_rows[index_row_1[0]][0] != self.connected_crop_rows[index_row_2[0]][0]:
                    #print("Connecting two existing crop rows")
                    #print("tile_1: ", tile_1_number)
                    #print("tile_2: ", tile_2_number)
                    #print("row: ", row)
                    self.connect_two_existing_full_crop_rows(index_row_1, tile_1_number, row[0], index_row_2, tile_2_number, row[1])
                unknown_crop_row = False

            elif index_row_1.size > 0:
                #self.connect_crop_row_to_existing_crop_row(tile_2_number, [row[1], row[4], row[5], row[2], row[3]], index_row_1)
                self.connect_crop_row_to_existing_crop_row(tile_2_number, row[1], tile_1_number, row[0], index_row_1)
                unknown_crop_row = False
                        
            elif index_row_2.size > 0:
                self.connect_crop_row_to_existing_crop_row(tile_1_number, row[0], tile_2_number, row[1], index_row_2)
                unknown_crop_row = False
                        
            if unknown_crop_row:
                self.connected_crop_rows = np.vstack((self.connected_crop_rows, np.array([self.crop_row_index, tile_1_number, row[0], tile_2_number, row[1], None, None, None, None, None, None, 0])))
                self.connected_crop_rows = np.vstack((self.connected_crop_rows, np.array([self.crop_row_index, tile_2_number, row[1], tile_1_number, row[0], None, None, None, None, None, None, 0])))
                self.crop_row_index += 1
        

    def connect_crop_row_to_existing_crop_row(self, new_tile_number: int, new_row: NDArray[Any], existing_tile_number: int, existing_row: NDArray[Any], index: NDArray[Any]) -> None:
        """
        Connect a crop row to an existing crop row
        """
        self.connected_crop_rows = np.vstack((self.connected_crop_rows, np.array([self.connected_crop_rows[index[0]][0], new_tile_number, new_row, existing_tile_number, existing_row, None, None, None, None, None, None, 0])))
        
        self.add_connection(new_tile_number, new_row, index)



        self.connections += 1

    def add_connection(self, tile_number, row, index):
        if self.connected_crop_rows[index[0], 5] is None:
            self.connected_crop_rows[index[0], 5] = tile_number
            self.connected_crop_rows[index[0], 6] = row
        elif self.connected_crop_rows[index[0], 7] is None:
            self.connected_crop_rows[index[0], 7] = tile_number
            self.connected_crop_rows[index[0], 8] = row
        elif self.connected_crop_rows[index[0], 9] is None:
            self.connected_crop_rows[index[0], 9] = tile_number
            self.connected_crop_rows[index[0], 10] = row
        else:
            print("No more space to add the crop row")
            print("row: ", tile_number)

            assert False, "A crop row tried to connect to more than 4 other crop rows, this is not possible"


    def connect_two_existing_full_crop_rows(self, index_row_1: NDArray[Any], tile_number_1: int, row_1, index_row_2: NDArray[Any], tile_number_2: int, row_2) -> None:
        """
        Connect two existing full crop rows
        """
        time_start = time()
        
        self.add_connection(tile_number_2, row_2, index_row_1)
        self.add_connection(tile_number_1, row_1, index_row_2)

        if index_row_1[0] < index_row_2[0]:
            self.move_row_and_adjust_indexes(index_row_1, index_row_2)
        else:
            self.move_row_and_adjust_indexes(index_row_2, index_row_1)
        self.connecting_full += 1
        self.connections += 1
        self.time_connect_full += (time() - time_start)
        


    def move_row_and_adjust_indexes(self, smallest_row_index: NDArray[Any], largest_row_index: NDArray[Any]) -> None:
        """
        Move rows together and adjust the indexes of all rows with a larger index
        """
        row_number_large = self.connected_crop_rows[largest_row_index[0]][0]
        row_number_small = self.connected_crop_rows[smallest_row_index[0]][0]
        row_index_to_change = np.array((self.connected_crop_rows[:, 0] == row_number_large).nonzero())

        for idx in row_index_to_change:
            self.connected_crop_rows[idx, 0] = row_number_small

        self.connected_crop_rows[self.connected_crop_rows[:, 0] > row_number_large, 0] = self.connected_crop_rows[self.connected_crop_rows[:, 0] > row_number_large, 0] - 1
        self.crop_row_index -= 1
        

    def add_unused_rows(self, tiles: list) -> None:
        """
        Add the unused rows to the connected crop rows
        """
        for tile in tiles.values():
            #print(f"tile rows: {tile.rows}")
            #print(f"tile unused rows: {tile.unused_rows}")
            for row in tile.unused_rows:
                #print("row: ", row)
                #print(f"row center: {tile.rows[int(row), 4]}")
                self.connected_crop_rows = np.vstack((self.connected_crop_rows, np.array([self.crop_row_index, tile.tile_number, row, None, None, None, None, None, None, None, None, 0])))
                self.crop_row_index += 1


    def sort_connected_crop_rows(self) -> None:
        """
        Sort the connected crop rows based on the tile number and then the row number
        """
        self.connected_crop_rows = self.connected_crop_rows[self.connected_crop_rows[:, 1].argsort()]
        self.connected_crop_rows = self.connected_crop_rows[self.connected_crop_rows[:, 0].argsort(kind='stable')]
        

    def check_dublicates(self) -> None:
        """
        Check for duplicates in the connected crop rows
        """
        # Check for duplicates in the first two columns (crop row index and tile number)
        DF_row_idx_tile = pd.DataFrame(self.connected_crop_rows[:, :2], columns=["crop_row_index", "tile_number"])
        duplicates = DF_row_idx_tile.duplicated(keep=False)
        duplicates = duplicates.replace({True: 1, False: 0})

        self.connected_crop_rows[:,11] = duplicates

