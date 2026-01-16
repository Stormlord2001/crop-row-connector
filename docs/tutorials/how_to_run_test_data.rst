Tutorial with test data
===============================

In this tutorial, we will guide you through the steps to run *crop-row-connector* using the provided test data.

The dataset includes two main files found in the `docs/test_dataset/input/` directory:
- A csv file containing the GPS coordinates of the crop rows.
- A csv file containing the GPS coordinates of all points in the orthomosaic.


A visual representation of all the points in the orthomosaic can be seen below:

.. figure:: ../figures/Field_detected.png

    detected crop rows in an orthomosaic

The orthomosaic from which the test data is derived can be found in the `docs/test_dataset/` directory as `orthomosaic_test_data.tif`, and can be viewed using georeferencer tools like QGIS.

To run the *crop-row-connector* with the test data, follow these steps:

1. **Clone the Repository**: If you haven't already, clone the *crop-row-connector* repository from GitHub to your local machine.
    .. code-block:: shell
    git clone https://github.com/Stormlord2001/crop-row-connector.git
    cd crop-row-connector


2. **create a Virtual Environment**: It is recommended to create a virtual environment to manage dependencies.
    .. code-block:: shell
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`


3. **Install Dependencies**: Install the required dependencies into the virtual environment using pip.
    .. code-block:: shell
    pip install .


4. **Run the Connector**: Use the following command to run the *crop-row-connector* with the test data. 
    .. code-block:: shell
    crop-row-connector docs/test_dataset/input/row_information_global.csv docs/test_dataset/input/points_in_rows.csv --output_path_connected_crop_rows docs/test_dataset/output/connected_crop_rows.csv --output_path_line_points docs/test_dataset/output/line_points.csv --distance_tolerance 0.12 --angle_tolerance 0.12
    

5. **View the Results**: After running the command, you will find the output files in the specified paths. You can visualize the connected crop rows and line points using georeferencer tools like QGIS.
