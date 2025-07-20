### **API Authentication Documentation**

Your Django project uses `djangorestframework-simplejwt` for token-based authentication. This is a secure and standard way to handle user authentication for decoupled frontends.

#### **Authentication Flow**

1.  **Register:** The user creates a new account.
2.  **Login:** The user signs in with their credentials, and the API returns an `access` token and a `refresh` token.
3.  **Make Authenticated Requests:** The frontend includes the `access` token in the `Authorization` header for all requests to protected API endpoints.
4.  **Refresh Token:** When the `access` token expires, the frontend uses the `refresh` token to get a new `access` token without requiring the user to log in again.
5.  **Logout:** The frontend deletes the tokens from local storage.

---

#### **API Endpoints**

**Base URL:** All endpoints are prefixed with `/api/`.

##### **1. User Registration**

Create a new user account.

*   **Endpoint:** `/register/`
*   **Method:** `POST`
*   **Request Body:**
    ```json
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "a-strong-password"
    }
    ```
*   **Response (Success `201 Created`):**
    ```json
    {
        "id": 1,
        "username": "newuser",
        "email": "user@example.com"
    }
    ```

##### **2. Login (Obtain Tokens)**

Authenticate a user and get their access and refresh tokens.

*   **Endpoint:** `/token/`
*   **Method:** `POST`
*   **Request Body:**
    ```json
    {
        "username": "newuser",
        "password": "a-strong-password"
    }
    ```
*   **Response (Success `200 OK`):
    ```json
    {
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    *Store both tokens securely on the client-side (e.g., in `localStorage`, `sessionStorage`, or Flutter's `flutter_secure_storage`).*

##### **3. Refresh Access Token**

Get a new access token using a refresh token.

*   **Endpoint:** `/token/refresh/`
*   **Method:** `POST`
*   **Request Body:**
    ```json
    {
        "refresh": "your-saved-refresh-token"
    }
    ```
*   **Response (Success `200 OK`):**
    ```json
    {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    *You should replace the old access token with this new one.*

---

#### **Making Authenticated Requests**

To access protected API endpoints, you must include the `access` token in the request header.

*   **Header:** `Authorization`
*   **Value:** `Bearer <your_access_token>`

**Example (using JavaScript `fetch`):**

```javascript
const accessToken = 'your_access_token'; // Retrieve the token from storage

fetch('https://your-api-domain.com/api/some-protected-endpoint/', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

#### **Logout**

Logout is handled entirely on the client-side. There is no API endpoint to call. Simply delete the `access` and `refresh` tokens from the client's storage. Once the tokens are gone, the user will be unable to access protected resources and will be considered logged out.
