/**
 * API Client for PVNDORA Backend
 */
import axios from 'axios';

const API_BASE = '/api';

// Create axios instance
const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Request interceptor to add auth header
export function setAuthHeader(initData) {
    if (initData) {
        api.defaults.headers.common['Authorization'] = `tma ${initData}`;
    }
}

// Products
export async function getProducts() {
    const { data } = await api.get('/products');
    return data;
}

export async function getProduct(productId) {
    const { data } = await api.get(`/products/${productId}`);
    return data;
}

// Orders
export async function createOrder(productId, promoCode = null) {
    const { data } = await api.post('/orders', {
        product_id: productId,
        promo_code: promoCode
    });
    return data;
}

export async function getOrders() {
    const { data } = await api.get('/orders');
    return data;
}

// User
export async function getUserProfile() {
    const { data } = await api.get('/user/profile');
    return data;
}

export async function getReferralInfo() {
    const { data } = await api.get('/user/referral');
    return data;
}

// Wishlist
export async function getWishlist() {
    const { data } = await api.get('/wishlist');
    return data;
}

export async function addToWishlist(productId) {
    const { data } = await api.post(`/wishlist/${productId}`);
    return data;
}

export async function removeFromWishlist(productId) {
    const { data } = await api.delete(`/wishlist/${productId}`);
    return data;
}

// FAQ
export async function getFaq(lang = 'en') {
    const { data } = await api.get(`/faq?lang=${lang}`);
    return data;
}

export default api;

