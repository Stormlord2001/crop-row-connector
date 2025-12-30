import pandas as pd  # type: ignore
import numpy as np  # type: ignore
from numpy.typing import NDArray  # type: ignore
from typing import Any  # type: ignore
import math  # type: ignore
import time  # type: ignore
import os  # type: ignore
from datetime import datetime  # type: ignore
from pathlib import Path  # type: ignore

# from icecream import ic # type: ignore
from tqdm import tqdm  # type: ignore
import matplotlib.pyplot as plt  # type: ignore

import crop_row_connector.find_connection_of_rows_between_two_tiles as find_connection_of_rows_between_two_tiles
import crop_row_connector.combine_crop_rows_from_connections as combine_crop_rows_from_connections

import crop_row_connector._native as mpro



class tile:
    def __init__(
        self, tile_number: int, position: list[float], angle: float, rows: NDArray[Any]
    ) -> None:
        self.tile_number = tile_number
        self.position = position
        self.angle = angle

        self.rows = rows
        self.unused_rows = rows[:, 0].astype(int).tolist()  # Row numbers


class Combine_crop_rows:
    def __init__(self):
        self.angle_tolerance = None
        self.output_path_connected_crop_rows = None
        self.output_path_line_points = None

        self.run_single_thread = True
        self.max_workers = os.cpu_count()

        self.ccbt = find_connection_of_rows_between_two_tiles.find_connection_of_rows_between_two_tiles()
        self.ccrc = (
            combine_crop_rows_from_connections.combine_crop_rows_from_connections()
        )

    def ensure_parent_directory_exist(self, path: Path):
        temp_path = path.parent
        if not temp_path.exists():
            temp_path.mkdir(parents=True)

    def load_csv(self, path: str) -> NDArray[Any]:
        """
        Load the csv file containing the row information
        """
        row_information = pd.read_csv(path).to_numpy()
        return row_information

    def seperate_row_information_to_tile(
        self, row_information: NDArray[Any]
    ) -> dict[int, tile]:
        """
        Seperate the row information to the different tiles
        """
        tile_numbers = np.unique(row_information[:, 0]).astype(int)
        # tile_numbers = tile_numbers[tile_numbers <= 1364]
        # tile_numbers = tile_numbers[tile_numbers >= 1238]
        print("Tile numbers: ", tile_numbers)

        # tile_numbers = [1294, 1295, 1354, 1355]
        # print("Tile numbers: ", tile_numbers)

        # assert False

        tiles = {}

        for tile_number in tile_numbers:
            rows_in_tile = row_information[row_information[:, 0] == tile_number]
            tile_position = rows_in_tile[0, 1:3].astype(int)
            row_angle = rows_in_tile[0, 3]
            rows = rows_in_tile[:, 4:]
            tile_load = tile(tile_number, tile_position, row_angle, rows)
            tiles.update({tile_number: tile_load})

        return tiles

    def create_tile_grid(
        self, row_information: NDArray[Any], tiles: dict[int, tile]
    ) -> NDArray[Any]:
        """
        Create a grid containing the tile numbers in their respective position and -1 for no tile
        """
        tile_grid_size = np.amax(row_information[:, 1:3], axis=0)

        grid = np.negative(
            np.ones((int(tile_grid_size[0] + 2), int(tile_grid_size[1] + 2)))
        )

        for tile in tiles.values():
            grid[tile.position[0], tile.position[1]] = tile.tile_number

        return grid

    def connect_rows_in_tiles(self, grid: NDArray[Any], tiles: dict[int, tile]) -> None:
        """
        Finds and connects the crop rows in the tiles
        """

        # x is indexing the columns and y is indexing the rows
        for y, x in tqdm(
            np.ndindex(grid.shape),
            total=grid.shape[0] * grid.shape[1],
            desc="Connecting rows in tiles",
            unit="tiles",
        ):
            tile_current = tiles.get(grid[y, x])
            if tile_current is not None:
                # Connect tile to the right
                tile_right = tiles.get(grid[y, x + 1])
                if tile_right is not None:
                    self.connect_2_tiles(tile_current, tile_right)

                # connect tile below
                tile_below = tiles.get(grid[y + 1, x])
                if tile_below is not None:
                    self.connect_2_tiles(tile_current, tile_below)

        print("removed connections: ", self.ccbt.removed_connections)
        print("removed padded connections: ", self.ccbt.removed_padded_connections)
        print("full connections", self.ccrc.connecting_full)
        print("connections", self.ccrc.connections)

        max = np.max(self.ccrc.connected_crop_rows[:, 0])
        max_idx = [0, 0]
        for i in range(0, int(max) + 1):
            # print(i, np.count_nonzero(self.ccrc.connected_crop_rows[self.ccrc.connected_crop_rows[:, 0] == i, 0]))
            if (
                np.count_nonzero(
                    self.ccrc.connected_crop_rows[
                        self.ccrc.connected_crop_rows[:, 0] == i, 0
                    ]
                )
                > max_idx[1]
            ):
                max_idx = [
                    i,
                    np.count_nonzero(
                        self.ccrc.connected_crop_rows[
                            self.ccrc.connected_crop_rows[:, 0] == i, 0
                        ]
                    ),
                ]
        print("crop row with most connections: ", max_idx)

        # add the uncombined rows to the connected crop rows
        self.ccrc.add_unused_rows(tiles)

    def connect_2_tiles(self, tile_1: tile | None, tile_2: tile | None) -> None:
        """
        Connect two tiles together
        """
        assert tile_1 is not None
        assert tile_2 is not None
        # Check if the angle of the two tiles is close enough
        if math.isclose(tile_1.angle, tile_2.angle, abs_tol=self.angle_tolerance):
            connections = self.ccbt.calculate_connections_between_2_tiles(
                tile_1, tile_2
            )
            self.ccrc.connect_crop_rows_of_2_tiles(
                tile_1.tile_number, tile_2.tile_number, connections
            )
        # else:
        # print(f"Angle difference between tile {tile_1.tile_number} and tile {tile_2.tile_number} is too large")

    def to_csv(self, connected_crop_rows: NDArray[Any]) -> None:
        """
        Write the connected crop rows to a csv file
        """
        # Write the connected crop rows to a csv file
        DF_connected_crop_rows = pd.DataFrame(
            connected_crop_rows,
            columns=[
                "row_index",
                "tile",
                "row",
                "con_1_tile",
                "con_1_row",
                "con_2_tile",
                "con_2_row",
                "con_3_tile",
                "con_3_row",
                "con_4_tile",
                "con_4_row",
                "dubli_error",
            ],
        )
        path = self.output_path_connected_crop_rows
        self.ensure_parent_directory_exist(Path(path))
        DF_connected_crop_rows.to_csv(path, index=False)

    def merge_all_points_in_all_crop_rows_remove(
        self,
        connected_crop_rows: NDArray[Any],
        path_points_in_rows: str,
        row_information: NDArray[Any],
        tiles: dict[int, tile],
    ) -> None:
        """
        Merge all points in all crop rows
        """

        DF_vegetation_rows = pd.read_csv(path_points_in_rows)

        tolerance = self.ccbt.distance_tolerance / 10

        start_time = time.time()
        crop_rows = mpro.merge_points_removing_overlap(connected_crop_rows.astype(np.float64), DF_vegetation_rows.to_numpy(), row_information, tolerance, self.max_workers)

        print("time to run loop: ", time.time() - start_time)

        #DF_crop_rows = pd.concat(crop_rows, ignore_index=True)
        DF_crop_rows = pd.DataFrame(crop_rows, columns=DF_vegetation_rows.columns)

        DF_crop_rows["vegetation"] = DF_crop_rows["vegetation"].astype(int)

        DF_connected_crop_rows = pd.DataFrame(
            connected_crop_rows[:, :3], columns=["crop_row", "tile", "row"]
        )

        DF_connected_crop_rows.insert(1, "duplicate", connected_crop_rows[:, -1])

        DF_crop_rows = pd.merge(
            DF_connected_crop_rows,
            DF_crop_rows,
            left_on=["tile", "row"],
            right_on=["tile", "row"],
            how="left",
        )
        DF_crop_rows = DF_crop_rows.drop(columns=["tile", "row"])
        DF_crop_rows = DF_crop_rows.rename(columns={"crop_row": "row"})
        DF_crop_rows = DF_crop_rows[["row", "x", "y", "vegetation", "duplicate"]]

        self.length_of_all_crop_rows(DF_crop_rows.to_numpy())

        path = self.output_path_line_points
        self.ensure_parent_directory_exist(Path(path))
        DF_crop_rows.to_csv(path, index=False)

        #print("Time to merge all points in all crop rows: ", time.time() - start_timer)

    def length_of_all_crop_rows(self, crop_rows: NDArray[Any]) -> float:
        """
        Calculate the length of all crop rows
        """

        total_time = 0.0

        length_low_vegetation = 0.0
        length_high_vegetation = 0.0

        total_field_length = 0.0
        total_length = 0.0
        curr_id = 0
        for i in range(len(crop_rows)-1):
            if crop_rows[i, 0] != curr_id:
                print("Length of crop row ", curr_id, ": ", total_length)
                curr_id = crop_rows[i, 0]
                total_field_length += total_length
                total_length = 0.0
                #assert False

            next_row = crop_rows[i + 1]

            time_start = time.time()
            length = np.linalg.norm(
                np.array([crop_rows[i, 1], crop_rows[i, 2]])
                - np.array([next_row[1], next_row[2]])
            )

            total_time += time.time() - time_start
            if length < self.ccbt.distance_tolerance:
                total_length += length
                if crop_rows[i, 3] < 20: # arbitrary threshold for low vegetation
                    length_low_vegetation += length
                else:
                    length_high_vegetation += length
        total_field_length += total_length
        print("Time to calculate length of all crop rows: ", total_time)
        print("Total length of all crop rows: ", total_field_length)
        print("Healthy vegetation length: ", length_high_vegetation)
        print("Low vegetation length: ", length_low_vegetation)
        return total_length

    def main(self, path_row_information: str, path_points_in_rows: str) -> None:
        time_start = time.time()
        row_information = self.load_csv(path_row_information)
        print("Time to load csv: ", time.time() - time_start)
        time_start = time.time()
        tiles = self.seperate_row_information_to_tile(row_information)
        # tiles = tiles[0:10]
        print("Time to seperate row information to tile: ", time.time() - time_start)
        time_start = time.time()
        grid = self.create_tile_grid(row_information, tiles)
        print("Time to create tile grid: ", time.time() - time_start)
        time_start = time.time()
        self.connect_rows_in_tiles(grid, tiles)
        print("Time to connect rows in tiles: ", time.time() - time_start)
        time_start = time.time()

        self.ccrc.sort_connected_crop_rows()

        self.ccrc.check_dublicates()

        print("Time to add unused rows: ", time.time() - time_start)
        time_start = time.time()
        self.to_csv(self.ccrc.connected_crop_rows)
        print("Time to combine crop rows: ", time.time() - time_start)

        time_write_start = time.time()
        self.merge_all_points_in_all_crop_rows_remove(
            self.ccrc.connected_crop_rows, path_points_in_rows, row_information, tiles
        )
        print("Time to write line points: ", time.time() - time_write_start)

    def save_statistics(self, stat_path, args, tiles):
        """
        Save the statistics of the run to a file
        """

        print(f'Writing statistics to the folder "{stat_path}"')

        with open(stat_path + "/output_file.txt", "w") as f:
            f.write("Input parameters:\n")
            f.write(f" - Segmented Orthomosaic: {args.segmented_orthomosaic}\n")
            f.write(f" - Orthomosaic: {args.orthomosaic}\n")
            f.write(f" - Tile sizes: {args.tile_size}\n")
            f.write(f" - Output tile location: {args.output_tile_location}\n")
            f.write(f" - Generated debug images: {args.generate_debug_images}\n")
            f.write(f" - Tile boundary: {args.tile_boundary}\n")
            f.write(
                f" - Ecpected crop row distance: {args.expected_crop_row_distance}\n"
            )
            f.write(
                f" - Date and time of execution: {datetime.now().replace(microsecond=0)}\n"
            )
            f.write("\n\nOutput from run\n")
            f.write(f" - Number of tiles: {len(tiles)}\n")
