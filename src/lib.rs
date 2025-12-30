use numpy::{IntoPyArray, PyArray2};
use pyo3::prelude::{pymodule, PyModule, PyResult, Python};



#[pymodule]
fn _native(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // The name of the module must match the package name
    #[pyfn(m)]
    fn merge_points_removing_overlap<'py>(
        py: Python<'py>,
        connected_crop_rows: &PyArray2<f64>,
        points_in_rows: &PyArray2<f64>,
        row_information: &PyArray2<f64>,
        tolerance: f64,
        num_threads: usize
    ) -> &'py PyArray2<f64> {
        // Convert the input PyArray2 to ndarray::Array2
        let c = connected_crop_rows.readonly().as_array().to_owned();
        let p = points_in_rows.readonly().as_array().to_owned();
        let r = row_information.readonly().as_array().to_owned();

        // Call the Rust function
        let result = rust_fn::multithreaded_merging(&c, &p, &r, tolerance, num_threads);

        result.into_pyarray(py)
    }
    Ok(())
}

mod rust_fn {
    use ndarray::{Array1, Array2, s};
    use std::time::Instant;
    use rayon::prelude::*;
    use indicatif::{ProgressBar, ProgressStyle};
    use ndarray::prelude::*;
    use std::sync::{Arc, Mutex};

    pub fn determine_points_relations(
        row1: &Array1<f64>,
        row2: &Array1<f64>,
    ) -> (Array1<f64>, Array1<f64>, Array1<f64>, Array1<f64>) {
        /*
        Given two lines with start and end point calculates which point on each line is 
        closest and farthest to the opposite line
        */
        // reshape skipping first element (row number)
        let r1 = row1.slice(s![1..]).to_owned().into_shape((3, 2)).unwrap();
        let r2 = row2.slice(s![1..]).to_owned().into_shape((3, 2)).unwrap();

        let mut max_dist = 0.0;
        let mut pair = (0, 0);
        for (i, a) in r1.axis_iter(ndarray::Axis(0)).enumerate() {
            for (j, b) in r2.axis_iter(ndarray::Axis(0)).enumerate() {
                let d = ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2)).sqrt();
                if d > max_dist {
                    max_dist = d;
                    pair = (i, j);
                }
            }
        }

        let row_1_far: ndarray::ArrayBase<ndarray::OwnedRepr<f64>, ndarray::Dim<[usize; 1]>> = r1.row(pair.0).to_owned();
        let row_2_far = r2.row(pair.1).to_owned();
        let row_1_close = if pair.0 == 0 { r1.row(1).to_owned() } else { r1.row(0).to_owned() };
        let row_2_close = if pair.1 == 0 { r2.row(1).to_owned() } else { r2.row(0).to_owned() };

        (row_1_far, row_2_far, row_1_close, row_2_close)
    }

    pub fn point_projection_of_p_onto_line(
        point: &Array1<f64>,
        l_close: &Array1<f64>,
        l_far: &Array1<f64>,
    ) -> Array1<f64> {
        /*
        Projects a point onto the line created by l_close and l_far
        */
        let v_line = l_far - l_close;
        let v_pc = point - l_close;
        let dot_vpc = v_pc.dot(&v_line);
        let dot_line = v_line.dot(&v_line);
        let scale = dot_vpc / dot_line;
        let proj_vec = scale * v_line;
        l_close + proj_vec
    }

    pub fn remove_points_past_center(
        center: &Array1<f64>,
        line_end: &Array1<f64>,
        rows: &Vec<Array1<f64>>,
        tolerance: f64,
    ) -> Vec<Array1<f64>> {
        /* 
        Removes points between the center and the end of a line if the center is on the line.
        */
        let selected_rows: Vec<Array1<f64>> = rows
            .iter()
            .filter(|r| {
                let x = r[2];
                let y = r[3];
                let distance = ((center[0] - line_end[0]).powi(2) + (center[1] - line_end[1]).powi(2)).sqrt();
                
                if distance < tolerance {
                    x == x && y == y
                } else if center[0] < line_end[0] && center[1] < line_end[1] {
                    (x <= center[0] + tolerance && y <= center[1] + tolerance)
                    || (x >= line_end[0] + tolerance && y >= line_end[1] + tolerance)
                } else if center[0] < line_end[0] && center[1] > line_end[1] {
                    (x <= center[0] + tolerance && y >= center[1] - tolerance)
                    || (x >= line_end[0] + tolerance && y <= line_end[1] - tolerance)
                } else if center[0] > line_end[0] && center[1] > line_end[1] {
                    (x >= center[0] - tolerance && y >= center[1] - tolerance)
                    || (x <= line_end[0] - tolerance && y <= line_end[1] - tolerance)
                } else {
                    (x >= center[0] - tolerance && y <= center[1] + tolerance)
                    || (x <= line_end[0] - tolerance && y >= line_end[1] + tolerance)
                }
            })
            .map(|r| r.to_owned())
            .collect();
        selected_rows

    }

    pub fn multithreaded_merging(
        connected_crop_rows: &Array2<f64>,
        points_in_rows: &Array2<f64>,
        row_information: &Array2<f64>,
        tolerance: f64,
        num_threads: usize,
    ) -> Array2<f64> {
        /*
        Merging the points in points_in_rows based on the information from connected_crop_rows.
        This is handled in a multithreaded manner. 
        */

        let start_total = Instant::now();

        rayon::ThreadPoolBuilder::new().num_threads(num_threads).build_global().unwrap();

        let merged_rows = Arc::new(Mutex::new(Vec::new()));
        let items: Vec<u64> = (0..connected_crop_rows.nrows() as u64).collect();
        let pb = Arc::new(ProgressBar::new(items.len() as u64));
        pb.set_style(ProgressStyle::with_template(
            "{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta})"
        ).unwrap());

        items.par_iter().for_each(|&i| {
            let row_segment = connected_crop_rows.row(i as usize);
            let rows = merge_points_removing_overlap(points_in_rows, row_information, tolerance, row_segment);
            // Use a Mutex to safely update the shared vector
            let mut merged_rows_lock = merged_rows.lock().unwrap();
            merged_rows_lock.extend(rows);
            pb.inc(1);
        });
        pb.finish_with_message("Processing complete");

        println!("total time: {}", start_total.elapsed().as_millis());
        let merged_rows = Arc::try_unwrap(merged_rows).unwrap().into_inner().unwrap();

        // Stack rows back into an Array2
        if merged_rows.is_empty() {
            return Array2::<f64>::zeros((0, points_in_rows.ncols()));
        }

        let ncols = merged_rows[0].len();
        let nrows = merged_rows.len();
        let flat: Vec<f64> = merged_rows.into_iter().flatten().collect();
        Array2::from_shape_vec((nrows, ncols), flat).unwrap()
    }

    fn merge_points_removing_overlap(
        points_in_rows: &ArrayBase<ndarray::OwnedRepr<f64>, Dim<[usize; 2]>>, 
        row_information: &ArrayBase<ndarray::OwnedRepr<f64>, Dim<[usize; 2]>>, 
        tolerance: f64, 
        row_segment: ArrayBase<ndarray::ViewRepr<&f64>, Dim<[usize; 1]>>
    ) -> Vec<ArrayBase<ndarray::OwnedRepr<f64>, Dim<[usize; 1]>>> {
        /*
        Takes a single row and removes points which overlap with other rows it is connected to it 
        */
        
        let tile_number = row_segment[1] as usize;
        let tile_row = row_segment[2] as usize;
    
        let mut rows = points_in_rows
            .axis_iter(ndarray::Axis(0))
            .filter(|r| r[0] as usize == tile_number && r[1] as usize == tile_row)
            .map(|r| r.to_owned())
            .collect::<Vec<_>>();
    
        let row = row_information
            .axis_iter(ndarray::Axis(0))
            .find(|r| r[0] as usize == tile_number && r[4] as usize == tile_row)
            .unwrap()
            .slice(s![4..])
            .to_owned();
    
        for i in 0..4 {
            if row_segment[3 + i * 2].is_nan() {
                break;
            }
            let connected_tile_n = row_segment[3 + i * 2];
            let connected_row_n = row_segment[4 + i * 2];
            let connected_row = row_information
                .axis_iter(ndarray::Axis(0))
                .find(|r| r[0] == connected_tile_n && r[4] == connected_row_n)
                .unwrap()
                .slice(s![4..])
                .to_owned();
    
    
            let (row_1_far, _, row_1_close, row_2_close) = determine_points_relations(
                &row,
                &connected_row,
            );
    
            let center_of_ends = (row_1_close.clone() + row_2_close) / 2.0;
    
            let point_proj = point_projection_of_p_onto_line(&center_of_ends, &row_1_close, &row_1_far);
    
            rows = remove_points_past_center(&point_proj, &row_1_close, &rows, tolerance);
    
        }
        rows
    }
}
