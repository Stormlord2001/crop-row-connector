Installation
============

*crop-row-connector* is a combined rust and python package.

It has the following main dependencies:

* rustc
* cargo
* pandas
* numpy
* tqdm
* matplotlib

It is recommended to install *crop-row-connector* using pip into a virtual environment, and can be done by running the following command in the root directory of the project:

.. code-block:: shell

    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install .

If it is preferred to install it system-wide, the virtual environment creation step can be skipped, but you first need to ensure that you have rustc installed on your system. You can download it from `https://rustup.rs/ <https://rustup.rs/>`_.

Once rustc is installed, you can install *crop-row-connector* by cloning the repository and then running the following command in the root directory of the project. This will build the rust extension and install the python package.

.. code-block:: shell

    pip install .