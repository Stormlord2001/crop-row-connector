import argparse
import os

import crop_row_connector.combine_crop_rows as Combine_crop_rows



parser = argparse.ArgumentParser(description='Combine crop rows')
parser.add_argument(
    "path_row_information", 
    type=str, 
    help='Path to the csv file containing the general information af the crop rows '
     '(tile number, tile position, row angle, row number, x1, y1, x2, y2 (start and end point of the row in the tile))'
)
parser.add_argument(
    "path_points_in_rows",
    type=str,
    help='Path to the csv file containing each point in the crop rows and their amount of vegetation '
     '(tile number, row number, x, y, vegetation)'
)
parser.add_argument(
    "--output_path_connected_crop_rows",
    default='connected_crop_rows.csv',
    type=str,
    help='Path to the output file, containing which crop rows where connected and from which tiles'
)
parser.add_argument(
    "--output_path_line_points",
    default='line_points.csv',
    type=str,
    help='Path to the output file, containing the points of the connected crop rows'
)
parser.add_argument(
    "--angle_tolerance",
    default=0.1,
    type=float,
    help='Angle tolerance for two crop rows to be connected'
)
parser.add_argument(
    "--distance_tolerance",
    default=10,
    type=float,
    help='Distance tolerance for two crop rows to be connected'
)
parser.add_argument(
    "--run_single_thread",
    action="store_true",
    help="If set the program will run in as a single thread. Default is to run in parallel.",
)
parser.add_argument(
    "--max_workers",
    default=os.cpu_count(),
    type=int,
    help="Set the maximum number of workers. Default to number of cpus.",
)

def _main():
    args = parser.parse_args()
    ccr = Combine_crop_rows.Combine_crop_rows()
    ccr.angle_tolerance = args.angle_tolerance
    ccr.ccbt.distance_tolerance = args.distance_tolerance
    ccr.output_path_connected_crop_rows = args.output_path_connected_crop_rows
    ccr.output_path_line_points = args.output_path_line_points
    ccr.run_single_thread = args.run_single_thread
    ccr.max_workers = args.max_workers
    ccr.main(args.path_row_information, args.path_points_in_rows)

if __name__ == "__main__":
    _main()
