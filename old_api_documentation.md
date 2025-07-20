# E-commerce API Documentation

This document outlines the key API endpoints for authentication, user management, and core e-commerce functionalities.

**Base URL:** `/api/` (assuming your Django project is served from the root)

---

## I. Authentication & User Management

### 1. User Registration

*   **Endpoint:** `/api/register/`
*   **Method:** `POST`
*   **Description:** Registers a new user.
*   **Request Body (JSON):**
    ```json
    {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "strongpassword123",
        "password2": "strongpassword123",
        "first_name": "New",
        "last_name": "User",
        "phone_number": "+998901234567",
        "address": "123 Main St",
        "is_seller": false
    }
    ```
*   **Response (JSON):**
    *   `201 Created`: User data (excluding password) and JWT tokens.
    *   `400 Bad Request`: Validation errors.

### 2. Token Obtain (Login)

*   **Endpoint:** `/api/token/`
*   **Method:** `POST`
*   **Description:** Obtains JWT access and refresh tokens for authentication.
*   **Request Body (JSON):**
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
*   **Response (JSON):**
    ```json
    {
        "refresh": "...",
        "access": "..."
    }
    ```
    *   `200 OK`: Tokens.
    *   `401 Unauthorized`: Invalid credentials.

### 3. Token Refresh

*   **Endpoint:** `/api/token/refresh/`
*   **Method:** `POST`
*   **Description:** Refreshes an expired access token using a valid refresh token.
*   **Request Body (JSON):**
    ```json
    {
        "refresh": "your_refresh_token"
    }
    ```
*   **Response (JSON):**
    ```json
    {
        "access": "new_access_token"
    }
    ```
    *   `200 OK`: New access token.
    *   `401 Unauthorized`: Invalid or expired refresh token.

### 4. Token Verify

*   **Endpoint:** `/api/token/verify/`
*   **Method:** `POST`
*   **Description:** Verifies if an access token is valid.
*   **Request Body (JSON):**
    ```json
    {
        "token": "your_access_token"
    }
    ```
*   **Response:**
    *   `200 OK`: If token is valid.
    *   `401 Unauthorized`: If token is invalid or expired.

### 5. User Profile (Authenticated User)

*   **Endpoint:** `/api/me/`
*   **Method:** `GET`, `PUT`, `PATCH`
*   **Description:** Retrieve or update the authenticated user's profile.
*   **Authentication:** Requires `Bearer <access_token>` in `Authorization` header.
*   **GET Response (JSON):** User details.
*   **PUT/PATCH Request Body (JSON):** Fields to update (e.g., `{"first_name": "Updated"}`).
*   **Response:**
    *   `200 OK`: Updated user data (for PUT/PATCH), or user data (for GET).
    *   `401 Unauthorized`: Not authenticated.
    *   `403 Forbidden`: Not authorized to perform action.
    *   `400 Bad Request`: Validation errors.

### 6. Logout

*   **API-based Logout:** JWT tokens are stateless. To "logout," the client simply needs to discard the `access` and `refresh` tokens. There's no specific API endpoint for invalidating them on the server side with `rest_framework_simplejwt` by default.

---

## II. Resource Management (CRUD Operations)

For all authenticated endpoints, include `Authorization: Bearer <access_token>` in the request headers.

### 1. Categories (`/api/categories/`)

*   **Permissions:** `IsAdminOrReadOnly` (Admins can CUD, others can R)
*   **List (GET):** `/api/categories/`
*   **Retrieve (GET):** `/api/categories/{id}/`
*   **Create (POST):** `/api/categories/`
    *   **Request Body:** `{"name": "Electronics", "slug": "electronics"}`
*   **Update (PUT/PATCH):** `/api/categories/{id}/`
    *   **Request Body:** `{"name": "Updated Category"}`
*   **Delete (DELETE):** `/api/categories/{id}/`

### 2. Products (`/api/products/`)

*   **Permissions:** `IsSellerOrAdmin` (Sellers/Admins can CUD their own/any products, others can R active products)
*   **List (GET):** `/api/products/` (Supports filtering: `?category=ID`, `?shop=ID`, `?available=true/false`; searching: `?search=keyword`; ordering: `?ordering=price`)
*   **Retrieve (GET):** `/api/products/{id}/`
*   **Create (POST):** `/api/products/`
    *   **Request Body:**
        ```json
        {
            "name": "New Product",
            "description": "A great new product.",
            "price": "99.99",
            "stock": 100,
            "category": 1,
            "available": true
            // "shop": 1 (only for admin, seller's shop is auto-assigned)
        }
        ```
*   **Update (PUT/PATCH):** `/api/products/{id}/`
*   **Delete (DELETE):** `/api/products/{id}/`

### 3. Product Images (`/api/product-images/`)

*   **Permissions:** `IsSellerOrAdmin`
*   **List (GET):** `/api/product-images/`
*   **Retrieve (GET):** `/api/product-images/{id}/`
*   **Create (POST):** `/api/product-images/` (Use `multipart/form-data` for image upload)
    *   **Request Body (Form Data):**
        *   `product`: ID of the product
        *   `image`: Image file
        *   `is_main`: `true` or `false`
*   **Update (PUT/PATCH):** `/api/product-images/{id}/`
*   **Delete (DELETE):** `/api/product-images/{id}/`

### 4. Users (`/api/users/`)

*   **Permissions:** `IsAdminUser` (Admins can list/create/destroy any user). Authenticated users can `retrieve`/`update`/`partial_update` their own profile via `/api/me/`.
*   **List (GET):** `/api/users/` (Admin only)
*   **Retrieve (GET):** `/api/users/{id}/` (Admin only, or self if `id` matches authenticated user's ID)
*   **Create (POST):** `/api/users/` (Admin only, or use `/api/register/` for general registration)
*   **Update (PUT/PATCH):** `/api/users/{id}/` (Admin only, or self via `/api/me/`)
*   **Delete (DELETE):** `/api/users/{id}/` (Admin only)

### 5. Shops (`/api/shops/`)

*   **Permissions:** `IsAuthenticatedOrReadOnly` (Authenticated users can manage their own shop, others read-only). `IsOwnerOrAdmin` for specific shop actions.
*   **List (GET):** `/api/shops/` (Shows active shops for unauthenticated, all for admin, own for seller)
*   **Retrieve (GET):** `/api/shops/{id}/`
*   **Create (POST):** `/api/shops/`
    *   **Request Body:** `{"name": "My Awesome Shop", "description": "Selling cool stuff."}` (Owner is auto-assigned to authenticated seller)
*   **Update (PUT/PATCH):** `/api/shops/{id}/`
*   **Delete (DELETE):** `/api/shops/{id}/`
*   **My Shop (GET):** `/api/shops/my_shop/` (Retrieves the authenticated seller's shop)

### 6. Orders (`/api/orders/`)

*   **Permissions:** `IsAuthenticated` (Users can see their own orders). `IsAdminUser` for list/update/delete. `IsSellerOrAdmin` for `update_status`.
*   **List (GET):** `/api/orders/` (Admin sees all, user sees own)
*   **Retrieve (GET):** `/api/orders/{id}/`
*   **Create (POST):** `/api/orders/` (Typically created via cart checkout)
*   **Update (PUT/PATCH):** `/api/orders/{id}/` (Admin only for `is_paid`, `status`)
*   **Delete (DELETE):** `/api/orders/{id}/` (Admin only)
*   **My Orders (GET):** `/api/orders/my_orders/` (Retrieves all orders for the authenticated user)
*   **Add Item (POST):** `/api/orders/{id}/add_item/` (Admin only)
    *   **Request Body:** `{"product": 1, "quantity": 2}`
*   **Update Status (POST):** `/api/orders/{id}/update_status/` (Admin/Seller)
    *   **Request Body:** `{"status": "SHIPPED"}` (Valid statuses: `PENDING`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `REFUNDED`)

### 7. Carts (`/api/carts/`)

*   **Permissions:** `IsAuthenticated` for general cart management. `AllowAny` for `my_cart`, `add_item`, `remove_item`, `checkout`.
*   **List (GET):** `/api/carts/` (Admin only)
*   **Retrieve (GET):** `/api/carts/{id}/` (Admin or owner)
*   **Create (POST):** `/api/carts/` (Explicit cart creation, usually handled by `my_cart` action)
*   **Update (PUT/PATCH):** `/api/carts/{id}/` (Admin or owner)
*   **Delete (DELETE):** `/api/carts/{id}/` (Admin or owner)
*   **My Cart (GET):** `/api/carts/my_cart/` (Retrieves authenticated user's cart or creates/retrieves anonymous cart based on session)
*   **Add Item (POST):** `/api/carts/add_item/`
    *   **Request Body:** `{"product_id": 1, "quantity": 1}`
*   **Remove Item (POST):** `/api/carts/remove_item/`
    *   **Request Body:** `{"product_id": 1, "quantity": 1}`
*   **Checkout (POST):** `/api/carts/checkout/`
    *   **Authentication:** Requires authenticated user.
    *   **Request Body:**
        ```json
        {
            "shipping_address_line1": "123 Main St",
            "shipping_city": "Anytown",
            "shipping_zip_code": "12345",
            "shipping_country": "USA",
            "shipping_address_line2": "Apt 101", // Optional
            "shipping_state": "CA", // Optional
            "billing_address_line1": "456 Oak Ave", // Optional, defaults to shipping if not provided
            "billing_city": "Otherville", // Optional
            "billing_zip_code": "67890", // Optional
            "billing_country": "USA", // Optional
            "billing_address_line2": "Suite 200", // Optional
            "billing_state": "NY" // Optional
        }
        ```

### 8. Reviews (`/api/reviews/`)

*   **Permissions:** `IsAuthenticatedOrReadOnly` (Authenticated users can create/edit, others read). `IsOwnerOrAdmin` for update/delete.
*   **List (GET):** `/api/reviews/` (Supports filtering by product: `?product_id=ID`)
*   **Retrieve (GET):** `/api/reviews/{id}/`
*   **Create (POST):** `/api/reviews/`
    *   **Request Body:** `{"product": 1, "rating": 5, "comment": "Great product!"}`
*   **Update (PUT/PATCH):** `/api/reviews/{id}/`
*   **Delete (DELETE):** `/api/reviews/{id}/`
*   **Get Reviews by Product (GET):** `/api/reviews/product/{product_id}/`

### 9. Likes (`/api/likes/`)

*   **Permissions:** `IsAuthenticated` for add/remove/check status. `AllowAny` for `get_likes_count`. `IsOwnerOrAdmin` for update/delete.
*   **Add Like (POST):** `/api/likes/{product_id}/`
*   **Remove Like (DELETE):** `/api/likes/{product_id}/`
*   **Check Like Status (GET):** `/api/likes/{product_id}/status/`
*   **Get Likes Count (GET):** `/api/likes/{product_id}/count/`

### 10. Comments (`/api/comments/`)

*   **Permissions:** `IsAuthenticatedOrReadOnly` (Authenticated users can create/edit, others read). `IsOwnerOrAdmin` for update/delete.
*   **List (GET):** `/api/comments/` (Supports filtering by product: `?product_id=ID`)
*   **Retrieve (GET):** `/api/comments/{id}/`
*   **Create (POST):** `/api/comments/`
    *   **Request Body:** `{"product": 1, "comment_text": "This is a comment."}`
*   **Update (PUT/PATCH):** `/api/comments/{id}/`
*   **Delete (DELETE):** `/api/comments/{id}/`
*   **Get Comments by Product (GET):** `/api/comments/product/{product_id}/`

---

## III. Analytics (Admin/Seller Specific)

*   **Permissions:** `IsAdminUser` for most. `IsSellerOrAdmin` for seller-specific analytics.

### 1. Total Product Sales (Admin)

*   **Endpoint:** `/api/analytics/total-product-sales/`
*   **Method:** `GET`
*   **Description:** Gets total sales quantity for top 10 products.

### 2. User Statistics (Admin)

*   **Endpoint:** `/api/analytics/user-statistics/`
*   **Method:** `GET`
*   **Description:** Gets user count by role.

### 3. Order Statistics (Admin)

*   **Endpoint:** `/api/analytics/order-statistics/`
*   **Method:** `GET`
*   **Description:** Gets total orders, total revenue, average order value.

### 4. Seller Product Sales (Seller/Admin)

*   **Endpoint:** `/api/analytics/seller-product-sales/`
*   **Method:** `GET`
*   **Description:** Gets total sales quantity for seller's top 10 products.

### 5. Seller Order Statistics (Seller/Admin)

*   **Endpoint:** `/api/analytics/seller-order-statistics/`
*   **Method:** `GET`
*   **Description:** Gets total orders and revenue for seller's products.

### 6. Seller Daily Sales Chart (Seller/Admin)

*   **Endpoint:** `/api/analytics/seller-daily-sales-chart/`
*   **Method:** `GET`
*   **Description:** Gets daily sales data for the last 30 days for seller's products.

---