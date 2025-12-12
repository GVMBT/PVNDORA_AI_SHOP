# PVNDORA Frontend Architecture

## Migration Status: React 19 + TypeScript Integration

**Last Updated:** December 2024  
**Build Status:** ✅ Passing  
**React Version:** 19.2.1

---

## 📁 Directory Structure

```
src/
├── adapters/                    # Data transformation layer
│   ├── index.ts                 # Barrel exports
│   ├── productAdapter.ts        # API → Component product data
│   ├── ordersAdapter.ts         # API → Component orders data
│   ├── profileAdapter.ts        # API → Component profile data
│   ├── leaderboardAdapter.ts    # API → Component leaderboard data
│   └── cartAdapter.ts           # API → Component cart data
│
├── components/
│   ├── new/                     # 🆕 New cyberpunk UI components
│   │   ├── index.ts             # Barrel exports
│   │   │
│   │   │ # Static Components (No API Data)
│   │   ├── Hero.tsx             # Landing hero section
│   │   ├── Navbar.tsx           # Navigation (sidebar + mobile)
│   │   ├── Footer.tsx           # Footer with links
│   │   ├── Guarantees.tsx       # Feature cards
│   │   ├── PandoraBox.tsx       # Animated 3D box SVG
│   │   ├── SupportChat.tsx      # Floating support widget
│   │   ├── CommandPalette.tsx   # CMD+K quick actions
│   │   ├── Legal.tsx            # Legal documents viewer
│   │   │
│   │   │ # Data Components (Mock Data - Development)
│   │   ├── Catalog.tsx          # Product grid
│   │   ├── ProductDetail.tsx    # Single product view
│   │   ├── Orders.tsx           # Order history
│   │   ├── Profile.tsx          # User profile + referrals
│   │   ├── Leaderboard.tsx      # Savings leaderboard
│   │   ├── CheckoutModal.tsx    # Cart + Payment
│   │   ├── AdminPanel.tsx       # Admin dashboard
│   │   │
│   │   │ # Connected Components (Real API - Production)
│   │   ├── CatalogConnected.tsx
│   │   ├── ProductDetailConnected.tsx
│   │   ├── OrdersConnected.tsx
│   │   ├── ProfileConnected.tsx
│   │   ├── LeaderboardConnected.tsx
│   │   └── CheckoutModalConnected.tsx
│   │
│   └── ui/                      # Legacy shadcn components
│
├── hooks/
│   ├── useApi.js                # Base API hook (initData auth)
│   ├── useApiTyped.ts           # 🆕 Typed API hooks
│   └── useTelegram.js           # Telegram WebApp SDK
│
├── types/
│   ├── api.ts                   # 🆕 Backend API response types
│   └── component.ts             # 🆕 Frontend component types
│
└── pages/                       # Legacy page components
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  Connected   │───▶│  useApiTyped │───▶│     Adapters          │  │
│  │  Component   │    │    Hooks     │    │  (Transform Data)     │  │
│  └──────────────┘    └──────────────┘    └───────────────────────┘  │
│         │                   │                      │                 │
│         │                   ▼                      ▼                 │
│         │            ┌──────────────┐    ┌───────────────────────┐  │
│         │            │   useApi     │    │   Component Types     │  │
│         │            │   (Base)     │    │   (src/types)         │  │
│         │            └──────────────┘    └───────────────────────┘  │
│         │                   │                                        │
│         ▼                   ▼                                        │
│  ┌──────────────┐    ┌──────────────┐                               │
│  │    Base      │    │  Telegram    │                               │
│  │  Component   │    │   initData   │                               │
│  │  (Render)    │    │   (Auth)     │                               │
│  └──────────────┘    └──────────────┘                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          BACKEND                                     │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Routes:                                                     │
│  • GET  /api/webapp/products          → APIProductsResponse         │
│  • GET  /api/webapp/products/:id      → APIProductResponse          │
│  • GET  /api/webapp/orders            → APIOrdersResponse           │
│  • GET  /api/webapp/profile           → APIProfileResponse          │
│  • GET  /api/webapp/leaderboard       → APILeaderboardResponse      │
│  • GET  /api/webapp/cart              → APICartResponse             │
│  • POST /api/webapp/orders            → APICreateOrderResponse      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Status Matrix

| Component | Base (Mock) | Connected (API) | Status |
|-----------|-------------|-----------------|--------|
| Hero | ✅ | N/A (Static) | ✅ Ready |
| Navbar | ✅ | N/A (Static) | ✅ Ready |
| Footer | ✅ | N/A (Static) | ✅ Ready |
| Guarantees | ✅ | N/A (Static) | ✅ Ready |
| PandoraBox | ✅ | N/A (Static) | ✅ Ready |
| SupportChat | ✅ | N/A (Static) | ✅ Ready |
| CommandPalette | ✅ | N/A (Static) | ✅ Ready |
| Legal | ✅ | N/A (Static) | ✅ Ready |
| **Catalog** | ✅ | ✅ `CatalogConnected` | ✅ Ready |
| **ProductDetail** | ✅ | ✅ `ProductDetailConnected` | ✅ Ready |
| **Orders** | ✅ | ✅ `OrdersConnected` | ✅ Ready |
| **Profile** | ✅ | ✅ `ProfileConnected` | ✅ Ready |
| **Leaderboard** | ✅ | ✅ `LeaderboardConnected` | ✅ Ready |
| **CheckoutModal** | ✅ | ✅ `CheckoutModalConnected` | ✅ Ready |
| AdminPanel | ✅ | ⏳ Pending | 🔶 Dev Only |

---

## 🔌 API Integration Points

### Products API
```typescript
// Endpoint: GET /api/webapp/products
// Response includes: sales_count, msrp, final_price, available_count

const { products, getProducts } = useProductsTyped();
// Returns: CatalogProduct[] with adapted data
```

### Profile API
```typescript
// Endpoint: GET /api/webapp/profile
// Response includes: click_count, conversion_rate in referral_stats

const { profile, getProfile } = useProfileTyped();
// Returns: ProfileData with career progress, billing logs
```

### Orders API
```typescript
// Endpoint: GET /api/webapp/orders
// Returns multi-item orders with status mapping

const { orders, getOrders, createOrder } = useOrdersTyped();
// Returns: Order[] with items, credentials, review status
```

### Leaderboard API
```typescript
// Endpoint: GET /api/webapp/leaderboard
// Returns top users by total_saved + current user rank

const { leaderboard, getLeaderboard } = useLeaderboardTyped();
// Returns: LeaderboardUser[] with rank, savings, trend
```

---

## 🔧 Backend Additions Required

### Database Schema Changes
```sql
-- Add referral click tracking
ALTER TABLE users
ADD COLUMN IF NOT EXISTS referral_clicks_count INTEGER DEFAULT 0;

-- RPC function for atomic increment
CREATE OR REPLACE FUNCTION increment_referral_click(user_id_param UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET referral_clicks_count = referral_clicks_count + 1
    WHERE id = user_id_param;
END;
$$ LANGUAGE plpgsql;

-- Extended referral stats view
CREATE OR REPLACE VIEW referral_stats_extended AS
SELECT 
    u.id as user_id,
    u.referral_clicks_count as click_count,
    CASE 
        WHEN u.referral_clicks_count > 0 
        THEN (COUNT(r.id)::float / u.referral_clicks_count * 100)
        ELSE 0 
    END as conversion_rate,
    -- ... other stats
FROM users u
LEFT JOIN users r ON r.referrer_id = u.id
GROUP BY u.id;
```

### API Endpoint Changes

| Endpoint | Field Added | Source |
|----------|-------------|--------|
| `/products` | `sales_count` | `product_social_proof` table |
| `/products/:id` | `sales_count` | `product_social_proof` table |
| `/profile` | `click_count` | `users.referral_clicks_count` |
| `/profile` | `conversion_rate` | Calculated from stats |

---

## 🚀 Usage Guide

### Development (Mock Data)
```tsx
import { Catalog, Profile, Orders } from './components/new';

function App() {
  return (
    <>
      <Catalog products={MOCK_PRODUCTS} />
      <Profile profile={MOCK_PROFILE} />
      <Orders orders={MOCK_ORDERS} />
    </>
  );
}
```

### Production (Real API)
```tsx
import { 
  CatalogConnected,
  ProfileConnected,
  OrdersConnected 
} from './components/new';

function App() {
  return (
    <>
      <CatalogConnected onSelectProduct={handleSelect} />
      <ProfileConnected onBack={handleBack} />
      <OrdersConnected onBack={handleBack} />
    </>
  );
}
```

### Full App Example
```tsx
import {
  Hero,
  Navbar,
  Footer,
  Guarantees,
  CatalogConnected,
  ProductDetailConnected,
  OrdersConnected,
  ProfileConnected,
  LeaderboardConnected,
  CheckoutModalConnected,
  SupportChat,
} from './components/new';

function App() {
  const [view, setView] = useState<ViewType>('home');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showCheckout, setShowCheckout] = useState(false);
  
  return (
    <div className="min-h-screen bg-black text-white">
      <Navbar 
        activeView={view}
        onNavigate={setView}
        cartCount={cartItems.length}
        onCartClick={() => setShowCheckout(true)}
      />
      
      {view === 'home' && (
        <>
          <Hero onCatalogClick={() => setView('catalog')} />
          <Guarantees />
        </>
      )}
      
      {view === 'catalog' && (
        <CatalogConnected 
          onSelectProduct={(p) => {
            setSelectedProduct(p);
            setView('product');
          }}
        />
      )}
      
      {view === 'product' && selectedProduct && (
        <ProductDetailConnected 
          productId={selectedProduct.id}
          initialProduct={selectedProduct}
          onBack={() => setView('catalog')}
        />
      )}
      
      {view === 'orders' && (
        <OrdersConnected onBack={() => setView('home')} />
      )}
      
      {view === 'profile' && (
        <ProfileConnected onBack={() => setView('home')} />
      )}
      
      {view === 'leaderboard' && (
        <LeaderboardConnected onBack={() => setView('home')} />
      )}
      
      {showCheckout && (
        <CheckoutModalConnected 
          onClose={() => setShowCheckout(false)}
          onSuccess={() => {
            setShowCheckout(false);
            setView('orders');
          }}
        />
      )}
      
      <Footer />
      <SupportChat />
    </div>
  );
}
```

---

## 📝 Migration Checklist

### Completed ✅
- [x] Copy new components to `src/components/new/`
- [x] Update React to v19.2.1
- [x] Create TypeScript types for API responses
- [x] Create TypeScript types for component props
- [x] Create data adapters layer
- [x] Create typed API hooks
- [x] Create Connected components for Catalog
- [x] Create Connected components for ProductDetail
- [x] Create Connected components for Orders
- [x] Create Connected components for Profile
- [x] Create Connected components for Leaderboard
- [x] Create Connected components for CheckoutModal
- [x] Add `sales_count` to products API
- [x] Add `click_count` to profile API
- [x] Verify build passes

### Pending 🔶
- [ ] Execute SQL migration for `referral_clicks_count`
- [ ] Create AdminPanel Connected component
- [ ] Full integration testing
- [ ] Remove mock data from base components (optional)
- [ ] Deploy and verify in production

---

## 🎨 Design System

### Colors (Tailwind)
```javascript
colors: {
  pandora: {
    cyan: '#00FFFF',
    dark: '#0a0a0a',
    darker: '#050505',
  }
}
```

### Fonts
```css
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400..900&family=Rajdhani:wght@300;400;500;600;700&display=swap');

font-family: {
  display: ['Orbitron', 'sans-serif'],  // Headers
  body: ['Rajdhani', 'sans-serif'],     // Body text
  mono: ['monospace'],                  // Code/data
}
```

### Key Visual Elements
- **Cyberpunk HUD aesthetic** - scanlines, glitch effects, neon accents
- **Dark background** (#0a0a0a) with cyan (#00FFFF) highlights
- **Terminal-style typography** - monospace for data, Orbitron for headers
- **Micro-interactions** - hover glows, 3D tilts, decrypt animations

---

## 🔒 Security Notes

- All API calls authenticated via Telegram `initData`
- Sensitive data (credentials) displayed with decrypt animation
- Payment processing through external gateways (RuKassa, CrystalPay)
- Admin features gated by `is_admin` flag from backend

---

## 📚 Related Documentation

- `docs/API_SPEC.md` - Full API specification
- `docs/DB_SCHEMA.md` - Database ERD and views
- `docs/async-architecture.md` - QStash patterns
- `docs/sequence-diagrams.md` - Process flows


