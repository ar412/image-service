# Image Upload Service

This service provides a serverless backend for uploading, managing, and viewing images, similar to a core feature of Instagram. It is built using AWS Lambda, API Gateway, S3, and DynamoDB.

The entire stack can be run locally using LocalStack for development and testing.

## Architecture

- **API Gateway**: Exposes the HTTP endpoints.
- **AWS Lambda**: Contains the business logic for each API endpoint.
- **Amazon S3**: Stores the raw image files.
- **Amazon DynamoDB**: Stores metadata associated with each image (e.g., filename, upload date, user-defined tags).

## Prerequisites

- Docker and Docker Compose
- Python 3.7+
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

## Using the Makefile

This project includes a `Makefile` to simplify common development tasks. It is the recommended way to interact with the project.

You can view all available commands by running:
```bash
make help
```

**Common Commands:**

- **`make install`**: Sets up the Python virtual environment and installs all dependencies.
  - Runs `make check-prereqs` to verify that `docker`, `sam`, and `python3` are installed.
  - Creates a virtual environment in `.venv` if one doesn't exist.
  - Installs production and development dependencies from `requirements.txt` and `requirements-dev.txt`.

- **`make run-local`**: Starts the LocalStack container.
  - Runs `docker-compose -f localstack-docker-compose.yml up -d` to start the local AWS environment in the background.

- **`make deploy-local`**: Builds and deploys the application to your local LocalStack environment.
  - Runs `sam build` to package the application.
  - Runs `sam deploy` to deploy the stack to LocalStack using the `[local]` profile from `samconfig.toml`.

- **`make stop-local`**: Stops the LocalStack container and removes its data.
  - Runs `docker-compose ... down --volumes` to stop the container and delete its data volume, ensuring a clean state for the next session.

- **`make test`**: Runs the unit test suite.
  - Runs `pytest` to execute all tests in the `tests/` directory.

- **`make clean`**: Removes temporary build files and the virtual environment.
  - Deletes the `.venv`, `.aws-sam`, and other cache directories to reset the project.

## Local Development Setup

The recommended setup process uses the provided `Makefile` for a streamlined experience.

1.  **Install Dependencies and Tools:**
    This single command will check for prerequisites, create a Python virtual environment, and install all required dependencies.
    ```bash
    make install
    ```

3.  **Configure AWS CLI for LocalStack (One-time setup):**
    To allow the AWS tools to communicate with your local environment, you need to create a dedicated `localstack` profile.

    **a. Add to `~/.aws/config`:**
    This file configures the region and points the CLI to your LocalStack container.
    ```ini
    [default]
    region = us-east-1
    output = json

    [profile localstack]
    region = us-east-1
    output = json
    endpoint_url = http://localhost:4566
    ```
    **b. Add to `~/.aws/credentials`:**
    This file provides the dummy credentials required by the CLI.
    ```ini
    [default]
    aws_access_key_id = test
    aws_secret_access_key = test

    [localstack]
    aws_access_key_id = test
    aws_secret_access_key = test
    ```

4.  **Start LocalStack:**
    This command starts the LocalStack container in the background.
    ```bash
    make run-local
    ```

5.  **Build and Deploy Locally:**
    This command will build and deploy the entire serverless application to your running LocalStack container.
    ```bash
    make deploy-local
    ```

6.  **Get the API URL:**
    After deployment, you can retrieve the API endpoint URL at any time.
    ```bash
    make get-url
    ```
    The URL will be used automatically by other `make api-*` commands. For manual `curl` requests, replace `{API_GATEWAY_URL}` in the examples below with this value.

### 1. Upload Image

- **Using `make`**:
    ```bash
    make api-upload FILE="./imageFiles/image1.jpg" DESC="image 1 sunset" TAGS="sunset,sky"
    make api-upload FILE="./imageFiles/image2.jpg" DESC="A beautiful sunset" TAGS="nature,sky"
    make api-upload FILE="./imageFiles/image3.png" DESC="image 3 png" TAGS="vacation,abstract"
    ```

---

- **Using `curl`**:

- **Endpoint**: `POST /images`
- **Description**: Uploads an image file along with its metadata. The request body must be `multipart/form-data`.
- **Form Fields**:
    - `file`: The image file to upload.
    - (optional) Any other key-value pairs will be stored as metadata (e.g., `description`, `tags`).
- **Example (`curl`)**:
    ```bash
    curl -X POST -F "file=@/path/to/your/image.jpg" -F "description=A beautiful sunset" -F "tags=nature,landscape" {API_GATEWAY_URL}/images
    ```
- **Success Response** (`201 Created`):
    ```json
    {
      "message": "Image uploaded successfully",
      "imageId": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    }
    ```

### 2. List Images

- **Using `make`**:
    ```bash
    # List all images
    make api-list
    
    # List all JPEGs
    make api-list TYPE=image/jpeg

    # List images with a specific tag
    make api-list TAGS=nature

    # Get a specific image by its ID
    make api-list ID=<image-id>
    ```

---

- **Endpoint**: `GET /images`
- **Description**: Retrieves a list of image metadata. This endpoint is optimized for performance:
    - If `imageId` is provided, it performs a direct, efficient lookup.
    - If `contentType` is provided, it uses a Global Secondary Index (GSI) for an efficient query.
    - Otherwise, it performs a paginated scan of the entire table.
- **Query Parameters**:
    - `imageId` (optional): Filter by a specific image ID.
    - `contentType` (optional): Filter by the image's content type (e.g., `image/jpeg`).
    - `nextToken` (optional): A token for pagination to retrieve the next set of results.
    ```bash
    # List all images (paginated scan)
    curl {API_GATEWAY_URL}/images

    # List all JPEGs (GSI query)
    curl "{API_GATEWAY_URL}/images?contentType=image/jpeg"

    # Get a specific image by ID (direct lookup)
    curl "{API_GATEWAY_URL}/images?imageId=<image-id>"

    # Fetch the next page of results
    curl "{API_GATEWAY_URL}/images?nextToken=eyJM...token...eyI="
    ```

### 3. View/Download Image

- **Using `make`**:
    ```bash
    make api-download ID=5e78a102-bd99-4bee-9ba3-fc27f48b7f0b OUT="./my_downloaded_image.jpg"
    ```

---

- **Using `curl`**:

- **Endpoint**: `GET /images/{imageId}`
- **Description**: Redirects to a temporary, presigned URL for the image file in S3. Your client (like a browser or `curl -L`) should follow the redirect.
    ```bash
    # The -L flag tells curl to follow the redirect
    curl -L {API_GATEWAY_URL}/images/{imageId} --output downloaded_image.jpg
    ```

### 4. Delete an Image

- **Using `make`**:
    ```bash
    make api-delete ID=<image-id-to-delete>
    ```

---

- **Using `curl`**:

- **Endpoint**: `DELETE /images/{imageId}`
- **Description**: Deletes the image from S3 and its corresponding metadata from DynamoDB.
    ```bash
    curl -X DELETE {API_GATEWAY_URL}/images/{imageId}
    ```

## Running Tests

This project uses `pytest` for unit testing and `moto` to mock AWS services. This allows for fast, isolated tests without needing a live AWS environment or LocalStack.

To run the tests:

```bash
source .venv/bin/activate
pip install -r requirements.txt # Ensure test dependencies are installed
pytest
```