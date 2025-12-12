
import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, ShoppingBag, Users, LifeBuoy, Settings, LogOut, 
  Search, Plus, Package, Edit, Trash2, ArrowUpRight, ArrowDownRight,
  BarChart3, Activity, DollarSign, CreditCard, Filter, ChevronRight, Save, X, MessageSquare, HelpCircle,
  Crown, User, Terminal, Clock, FileText, AlertCircle, CheckCircle, Send, Menu, Key, Shield, Zap, Globe, 
  Image as ImageIcon, Upload, Video
} from 'lucide-react';

interface AdminPanelProps {
  onExit: () => void;
}

type AdminView = 'dashboard' | 'catalog' | 'sales' | 'partners' | 'support';

// --- MOCK DATA ---

const MOCK_PRODUCTS = [
    { 
        id: 1, 
        name: "Nano Banana Pro", 
        category: "Text",
        description: "Full access to GPT-4 Turbo via decentralized nodes.",
        price: 299, 
        msrp: 500, 
        type: "Instant", 
        stock: 12, 
        fulfillment: 0, 
        warranty: 720, 
        duration: 30, 
        sold: 1542, 
        vpn: true,
        image: "https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=800&auto=format&fit=crop",
        video: "https://youtube.com/watch?v=dQw4w9WgXcQ",
        instructions: "1. Download client.\n2. Enter key." 
    },
    { 
        id: 2, 
        name: "Veo 3.1", 
        category: "Video",
        description: "High-fidelity video generation model.",
        price: 450, 
        msrp: 800, 
        type: "Instant", 
        stock: 0, 
        fulfillment: 0, 
        warranty: 168, 
        duration: 30, 
        sold: 890, 
        vpn: false,
        image: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop",
        instructions: "Login via web portal." 
    },
    { 
        id: 3, 
        name: "Claude Max", 
        category: "Text",
        description: "Large context window model.",
        price: 350, 
        msrp: 600, 
        type: "Preorder", 
        stock: 5, 
        fulfillment: 24, 
        warranty: 720, 
        duration: 30, 
        sold: 430, 
        vpn: true,
        image: "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=800&auto=format&fit=crop",
        instructions: "Wait for invite." 
    },
];

const MOCK_ORDERS = [
    { id: "ORD-9921", user: "@neon_runner", product: "Nano Banana Pro", amount: 299, status: "PAID", date: "10m ago", method: "CRYPTO" },
    { id: "ORD-9920", user: "@crypto_whale", product: "Veo 3.1", amount: 450, status: "REFUNDED", date: "2h ago", method: "CARD" },
    { id: "ORD-9919", user: "@anon_x", product: "Claude Max", amount: 350, status: "PAID", date: "5h ago", method: "INTERNAL" },
    { id: "ORD-9918", user: "@user_001", product: "Midjourney V6", amount: 400, status: "FAILED", date: "1d ago", method: "CARD" },
    { id: "ORD-8812", user: "@matrix_fan", product: "Nano Banana Pro", amount: 299, status: "PAID", date: "1d ago", method: "CRYPTO" },
];

const MOCK_TICKETS = [
    { 
        id: "TCK-9921", user: "@neon_runner", subject: "Auth Token Invalid", status: "OPEN", priority: "HIGH", date: "10m ago",
        history: [{ sender: 'user', text: "Token gives 403 error.", time: "10:00" }]
    },
    { 
        id: "TCK-9920", user: "@crypto_whale", subject: "Payment not credited", status: "CLOSED", priority: "MEDIUM", date: "2h ago",
        history: [{ sender: 'user', text: "Sent USDT, pending.", time: "08:30" }]
    },
];

const MOCK_PARTNERS = [
    { id: 1, handle: "@crypto_whale", level: "ARCHITECT", totalRef: 450, earned: 12500, status: "ACTIVE", rewardType: "commission" },
    { id: 2, handle: "@sub_zero", level: "OPERATOR", totalRef: 12, earned: 450, status: "ACTIVE", rewardType: "commission" },
    { id: 3, handle: "@ghost_shell", level: "PROXY", totalRef: 0, earned: 0, status: "INACTIVE", rewardType: "commission" },
];

const VIP_REQUESTS = [
    { id: 101, handle: "@tech_blogger_ru", source: "YouTube (150k)", message: "Want to review Veo 3.1 for my channel.", date: "1h ago" },
    { id: 102, handle: "@ai_course_lead", source: "Online School", message: "Need bulk access for 50 students.", date: "5h ago" },
];

// --- COMPONENTS ---

const AdminPanel: React.FC<AdminPanelProps> = ({ onExit }) => {
  const [currentView, setCurrentView] = useState<AdminView>('dashboard');
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Sales State
  const [orderSearch, setOrderSearch] = useState('');

  // Partners State
  const [activePartnerTab, setActivePartnerTab] = useState<'list' | 'requests'>('list');
  const [editingPartner, setEditingPartner] = useState<any>(null);

  // Catalog State
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<any>(null);
  const [productTab, setProductTab] = useState<'general' | 'inventory'>('general');
  const [inventoryText, setInventoryText] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Support State
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  // --- HANDLERS ---
  
  // Product Logic
  const handleEditProduct = (product: any) => {
      setEditingProduct(product);
      setProductTab('general');
      setInventoryText('');
      setIsProductModalOpen(true);
  };

  const handleNewProduct = () => {
      setEditingProduct({ 
          name: '', price: 0, stock: 0, category: 'Text', 
          image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=800&auto=format&fit=crop' // Default placeholder
      });
      setProductTab('general');
      setInventoryText('');
      setIsProductModalOpen(true);
  };

  const handleStockUpdate = () => {
      const lines = inventoryText.split('\n').filter(line => line.trim() !== '');
      if (editingProduct) {
          setEditingProduct({ ...editingProduct, stock: (editingProduct.stock || 0) + lines.length });
      }
      setInventoryText('');
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
          const reader = new FileReader();
          reader.onloadend = () => {
              setEditingProduct({ ...editingProduct, image: reader.result as string });
          };
          reader.readAsDataURL(file);
      }
  };

  const triggerFileInput = () => {
      fileInputRef.current?.click();
  };

  // Partner Logic
  const handleEditPartner = (partner: any) => {
      setEditingPartner(partner);
  };

  const togglePartnerVip = () => {
      if (editingPartner) {
          // If already architect, demote to proxy, otherwise promote
          setEditingPartner({
              ...editingPartner,
              level: editingPartner.level === 'ARCHITECT' ? 'PROXY' : 'ARCHITECT'
          });
      }
  };

  const toggleRewardType = () => {
      if (editingPartner) {
          setEditingPartner({
              ...editingPartner,
              rewardType: editingPartner.rewardType === 'commission' ? 'discount' : 'commission'
          });
      }
  };

  // --- SUB-VIEWS RENDERERS ---

  const renderDashboard = () => (
      <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Revenue" value="₽ 4.2M" trend="+12%" icon={<DollarSign size={20} />} />
              <StatCard label="Active Orders" value="142" trend="+5%" icon={<ShoppingBag size={20} />} />
              <StatCard label="Total Users" value="8,920" trend="+24" icon={<Users size={20} />} />
              <StatCard label="Open Tickets" value="15" trend="-2" isNegative={false} icon={<LifeBuoy size={20} />} />
          </div>
          {/* Charts placeholder */}
          <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm h-64 flex items-end justify-between gap-2">
               {[...Array(12)].map((_, i) => (
                   <div key={i} className="flex-1 bg-white/5 hover:bg-pandora-cyan transition-colors" style={{ height: `${Math.random() * 80 + 20}%` }} />
               ))}
          </div>
      </div>
  );

  const renderCatalog = () => (
      <div className="space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
              <div className="relative w-full md:w-auto">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
                  <input type="text" placeholder="Search SKU..." className="w-full md:w-64 bg-black border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none" />
              </div>
              <button onClick={handleNewProduct} className="w-full md:w-auto flex items-center justify-center gap-2 bg-pandora-cyan text-black px-4 py-2 text-xs font-bold uppercase hover:bg-white transition-colors">
                  <Plus size={14} /> Add Product
              </button>
          </div>

          {/* Desktop Table */}
          <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-white/5 text-gray-400 uppercase">
                      <tr>
                          <th className="p-4">Name</th>
                          <th className="p-4">Category</th>
                          <th className="p-4">Price / MSRP</th>
                          <th className="p-4">Stock</th>
                          <th className="p-4 text-right">Actions</th>
                      </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-gray-300">
                      {MOCK_PRODUCTS.map(p => (
                          <tr key={p.id} className="hover:bg-white/5 transition-colors">
                              <td className="p-4 font-bold text-white flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-sm overflow-hidden bg-black border border-white/10">
                                      <img src={p.image} alt="" className="w-full h-full object-cover" />
                                  </div>
                                  {p.name}
                              </td>
                              <td className="p-4"><span className="text-[10px] bg-white/5 px-2 py-1 rounded">{p.category}</span></td>
                              <td className="p-4">
                                  <div>{p.price} ₽</div>
                                  {p.msrp && <div className="text-[10px] text-gray-500 line-through">{p.msrp} ₽</div>}
                              </td>
                              <td className="p-4"><StockIndicator stock={p.stock} /></td>
                              <td className="p-4 text-right">
                                  <button onClick={() => handleEditProduct(p)} className="hover:text-pandora-cyan p-1"><Edit size={14} /></button>
                              </td>
                          </tr>
                      ))}
                  </tbody>
              </table>
          </div>

          {/* Mobile Cards */}
          <div className="md:hidden space-y-4">
              {MOCK_PRODUCTS.map(p => (
                  <div key={p.id} className="bg-[#0e0e0e] border border-white/10 p-4 flex justify-between items-center">
                      <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-sm overflow-hidden bg-black border border-white/10 shrink-0">
                              <img src={p.image} alt="" className="w-full h-full object-cover" />
                          </div>
                          <div>
                              <div className="font-bold text-white mb-1">{p.name}</div>
                              <div className="text-xs text-gray-500 mb-2">{p.category} • {p.price} ₽</div>
                              <StockIndicator stock={p.stock} />
                          </div>
                      </div>
                      <button onClick={() => handleEditProduct(p)} className="p-2 border border-white/10 rounded-full text-gray-400 hover:text-white hover:border-pandora-cyan"><Edit size={16} /></button>
                  </div>
              ))}
          </div>
      </div>
  );

  const renderSales = () => {
      const filteredOrders = MOCK_ORDERS.filter(o => 
          o.id.toLowerCase().includes(orderSearch.toLowerCase()) || 
          o.user.toLowerCase().includes(orderSearch.toLowerCase())
      );

      return (
      <div className="space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <h3 className="font-display font-bold text-white uppercase text-lg">Transactions</h3>
              <div className="relative w-full md:w-auto">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
                  <input 
                    type="text" 
                    placeholder="Search Order ID or User..." 
                    value={orderSearch}
                    onChange={(e) => setOrderSearch(e.target.value)}
                    className="w-full md:w-64 bg-[#0e0e0e] border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none" 
                  />
              </div>
          </div>

          <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
              <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-white/5 text-gray-400 uppercase">
                      <tr>
                          <th className="p-4">Order ID</th>
                          <th className="p-4">User</th>
                          <th className="p-4">Product</th>
                          <th className="p-4">Status</th>
                          <th className="p-4 text-right">Date</th>
                      </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-gray-300">
                      {filteredOrders.map(o => (
                          <tr key={o.id} className="hover:bg-white/5 transition-colors cursor-pointer">
                              <td className="p-4 font-bold text-pandora-cyan">{o.id}</td>
                              <td className="p-4 text-gray-400">{o.user}</td>
                              <td className="p-4 font-bold text-white">{o.product}</td>
                              <td className="p-4"><StatusBadge status={o.status} /></td>
                              <td className="p-4 text-right text-gray-500">{o.date}</td>
                          </tr>
                      ))}
                  </tbody>
              </table>
          </div>

          {/* Mobile Orders */}
          <div className="md:hidden space-y-4">
              {filteredOrders.map(o => (
                  <div key={o.id} className="bg-[#0e0e0e] border border-white/10 p-4 space-y-3">
                      <div className="flex justify-between items-center">
                          <span className="font-bold text-pandora-cyan text-sm">{o.id}</span>
                          <span className="text-[10px] text-gray-500">{o.date}</span>
                      </div>
                      <div className="text-sm text-white font-bold">{o.product}</div>
                      <div className="flex justify-between items-center text-xs">
                          <span className="text-gray-400">{o.user}</span>
                          <StatusBadge status={o.status} />
                      </div>
                  </div>
              ))}
          </div>
      </div>
      );
  };

  const renderPartners = () => (
      <div className="space-y-6">
          <div className="flex gap-4 border-b border-white/10 pb-1 overflow-x-auto">
              <button 
                onClick={() => setActivePartnerTab('list')}
                className={`text-xs font-bold uppercase pb-2 px-2 transition-colors ${activePartnerTab === 'list' ? 'text-pandora-cyan border-b-2 border-pandora-cyan' : 'text-gray-500'}`}
              >
                  Partner List
              </button>
              <button 
                onClick={() => setActivePartnerTab('requests')}
                className={`text-xs font-bold uppercase pb-2 px-2 transition-colors ${activePartnerTab === 'requests' ? 'text-pandora-cyan border-b-2 border-pandora-cyan' : 'text-gray-500'}`}
              >
                  VIP Requests <span className="ml-1 bg-red-500 text-white px-1 rounded-sm text-[9px]">{VIP_REQUESTS.length}</span>
              </button>
          </div>

          {activePartnerTab === 'list' ? (
              <>
                <div className="bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden hidden md:block">
                    <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-white/5 text-gray-400 uppercase">
                            <tr>
                                <th className="p-4">Handle</th>
                                <th className="p-4">Rank</th>
                                <th className="p-4">Earnings</th>
                                <th className="p-4">Reward Mode</th>
                                <th className="p-4">Status</th>
                                <th className="p-4">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-gray-300">
                            {MOCK_PARTNERS.map(p => (
                                <tr key={p.id} className="hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-white">{p.handle}</td>
                                    <td className="p-4"><span className={`text-[10px] px-2 py-0.5 border ${p.level === 'ARCHITECT' ? 'border-yellow-500 text-yellow-500' : 'border-gray-500 text-gray-500'}`}>{p.level}</span></td>
                                    <td className="p-4 text-pandora-cyan">₽ {p.earned}</td>
                                    <td className="p-4 text-[10px] uppercase text-gray-400">{p.rewardType === 'commission' ? '💰 Commission' : '🎁 Ref Discount'}</td>
                                    <td className="p-4"><StatusBadge status={p.status} /></td>
                                    <td className="p-4"><button onClick={() => handleEditPartner(p)} className="hover:text-pandora-cyan"><Edit size={14} /></button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {/* Mobile Partners */}
                <div className="md:hidden space-y-4">
                    {MOCK_PARTNERS.map(p => (
                        <div key={p.id} className="bg-[#0e0e0e] border border-white/10 p-4 relative">
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-bold text-white">{p.handle}</span>
                                <StatusBadge status={p.status} />
                            </div>
                            <div className="text-xs text-gray-500 mb-2">{p.level} • Earned: {p.earned} ₽</div>
                            <button onClick={() => handleEditPartner(p)} className="w-full text-[10px] bg-white/5 py-2 hover:bg-pandora-cyan hover:text-black transition-colors">MANAGE</button>
                        </div>
                    ))}
                </div>
              </>
          ) : (
              <div className="grid grid-cols-1 gap-4">
                  {VIP_REQUESTS.map(req => (
                      <div key={req.id} className="bg-[#0e0e0e] border border-white/10 p-4 flex flex-col md:flex-row justify-between gap-4">
                          <div>
                              <div className="flex items-center gap-2 font-bold text-white mb-1">
                                  {req.handle} <span className="text-[10px] font-normal text-gray-500 bg-white/5 px-2 rounded">{req.source}</span>
                              </div>
                              <p className="text-xs text-gray-400 font-mono">"{req.message}"</p>
                              <div className="text-[9px] text-gray-600 mt-2">{req.date}</div>
                          </div>
                          <div className="flex gap-2 items-center">
                              <button className="px-3 py-2 bg-green-900/20 text-green-500 border border-green-500/30 text-[10px] font-bold uppercase hover:bg-green-500 hover:text-black transition-colors">Approve</button>
                              <button className="px-3 py-2 bg-red-900/20 text-red-500 border border-red-500/30 text-[10px] font-bold uppercase hover:bg-red-500 hover:text-black transition-colors">Reject</button>
                          </div>
                      </div>
                  ))}
              </div>
          )}
      </div>
  );

  const renderSupport = () => (
      // Reuse existing support logic but adapted for mobile container
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
          {/* Ticket List */}
          <div className={`${selectedTicketId ? 'hidden lg:block' : 'block'} lg:col-span-1 space-y-4 overflow-y-auto pr-2`}>
              <div className="flex justify-between items-center mb-2">
                  <h3 className="font-display font-bold text-white">INBOX</h3>
                  <div className="text-xs font-mono text-gray-500">2 OPEN</div>
              </div>
              {MOCK_TICKETS.map(t => (
                  <div 
                      key={t.id} 
                      onClick={() => setSelectedTicketId(t.id)}
                      className={`bg-[#0e0e0e] border p-4 transition-colors cursor-pointer group relative ${selectedTicketId === t.id ? 'border-pandora-cyan bg-pandora-cyan/5' : 'border-white/10 hover:border-white/30'}`}
                  >
                      <div className="flex justify-between items-start mb-2">
                          <span className="text-[10px] font-mono text-gray-500">{t.id}</span>
                          <span className="text-[10px] font-mono text-gray-600">{t.date}</span>
                      </div>
                      <div className="font-bold text-white text-sm mb-1">{t.subject}</div>
                      <div className="text-xs text-gray-400">{t.user}</div>
                  </div>
              ))}
          </div>

          {/* Chat Area */}
          <div className={`${!selectedTicketId ? 'hidden lg:flex' : 'flex'} lg:col-span-2 bg-[#0e0e0e] border border-white/10 flex-col h-full relative`}>
              {selectedTicketId ? (
                  <>
                      <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/50">
                          <div className="flex items-center gap-3">
                              <button onClick={() => setSelectedTicketId(null)} className="lg:hidden text-gray-500"><ArrowUpRight className="rotate-[-135deg]" size={20}/></button>
                              <h3 className="font-bold text-white">TCK-{selectedTicketId.split('-')[1]}</h3>
                          </div>
                          <button className="text-green-500 text-[10px] border border-green-500/30 px-3 py-1">RESOLVE</button>
                      </div>
                      <div className="flex-1 p-4 overflow-y-auto"><div className="text-center text-gray-600 text-xs mt-10">End of encryption history</div></div>
                      <div className="p-4 border-t border-white/10"><input placeholder="Type response..." className="w-full bg-black border border-white/20 p-3 text-xs text-white outline-none" /></div>
                  </>
              ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-gray-600 opacity-50">
                      <MessageSquare size={48} className="mb-4" />
                      <span className="font-mono text-xs uppercase tracking-widest">Select Ticket</span>
                  </div>
              )}
          </div>
      </div>
  );

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-black text-white flex flex-col md:flex-row overflow-hidden"
    >
        {/* === MOBILE HEADER === */}
        <div className="md:hidden h-16 border-b border-white/10 flex items-center justify-between px-4 bg-[#050505] z-50 relative">
            <div className="font-display font-bold text-white tracking-widest flex items-center gap-2">
                <Terminal className="text-red-500" size={18} /> ADMIN
            </div>
            <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="text-white"><Menu size={24} /></button>
        </div>

        {/* === SIDEBAR (Responsive) === */}
        <div className={`
            fixed md:static inset-0 z-40 bg-[#050505] border-r border-white/10 transition-transform duration-300 flex flex-col
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
            ${isSidebarCollapsed ? 'md:w-20' : 'md:w-64'}
            w-64
        `}>
            <div 
                className="hidden md:flex h-20 items-center px-6 border-b border-white/10 cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => setSidebarCollapsed(!isSidebarCollapsed)}
                title="Toggle Sidebar"
            >
                <Terminal className="text-red-500 mr-3 shrink-0" />
                {!isSidebarCollapsed && (
                    <div className="overflow-hidden whitespace-nowrap">
                        <div className="font-display font-bold text-lg tracking-widest text-white">ADMIN</div>
                        <div className="text-[9px] font-mono text-red-500 uppercase">Root Access</div>
                    </div>
                )}
            </div>
            
            <div className="flex-1 py-6 space-y-1 px-3 mt-16 md:mt-0">
                <AdminNavItem icon={<LayoutDashboard size={18} />} label="Dashboard" active={currentView === 'dashboard'} onClick={() => {setCurrentView('dashboard'); setSidebarOpen(false);}} collapsed={isSidebarCollapsed} />
                <AdminNavItem icon={<Package size={18} />} label="Catalog & Stock" active={currentView === 'catalog'} onClick={() => {setCurrentView('catalog'); setSidebarOpen(false);}} collapsed={isSidebarCollapsed} />
                <AdminNavItem icon={<BarChart3 size={18} />} label="Sales & Orders" active={currentView === 'sales'} onClick={() => {setCurrentView('sales'); setSidebarOpen(false);}} collapsed={isSidebarCollapsed} />
                <AdminNavItem icon={<Users size={18} />} label="Partners & VIP" active={currentView === 'partners'} onClick={() => {setCurrentView('partners'); setSidebarOpen(false);}} collapsed={isSidebarCollapsed} />
                <AdminNavItem icon={<LifeBuoy size={18} />} label="Support" active={currentView === 'support'} onClick={() => {setCurrentView('support'); setSidebarOpen(false);}} collapsed={isSidebarCollapsed} />
            </div>

            <div className="p-4 border-t border-white/10">
                <button onClick={onExit} className={`flex items-center gap-3 w-full text-gray-500 hover:text-white transition-colors p-2 rounded-sm hover:bg-white/5 ${isSidebarCollapsed ? 'justify-center' : ''}`}>
                    <LogOut size={18} />
                    {!isSidebarCollapsed && <span className="text-sm font-bold uppercase">Exit System</span>}
                </button>
            </div>
        </div>

        {/* Overlay for mobile sidebar */}
        {isSidebarOpen && <div className="fixed inset-0 bg-black/80 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}

        {/* === MAIN CONTENT === */}
        <div className="flex-1 min-w-0 bg-[#080808] h-[calc(100vh-64px)] md:h-screen overflow-y-auto">
            {/* Top Header (Desktop) */}
            <div className="hidden md:flex h-20 border-b border-white/10 justify-between items-center px-8 bg-[#050505] sticky top-0 z-30">
                <div>
                    <h2 className="text-2xl font-display font-bold text-white uppercase">{currentView}</h2>
                    <div className="text-[10px] font-mono text-gray-500">LAST_LOGIN: 2025.10.02 // 14:00</div>
                </div>
                <div className="flex items-center gap-4">
                     <div className="text-right">
                         <div className="text-xs font-bold text-white">AdminUser_01</div>
                         <div className="text-[10px] text-green-500 font-mono">ONLINE</div>
                     </div>
                     <div className="w-10 h-10 bg-red-900/20 border border-red-500/50 rounded-sm flex items-center justify-center text-red-500">
                         <Settings size={20} />
                     </div>
                </div>
            </div>

            {/* View Content */}
            <div className="p-4 md:p-8 pb-24 md:pb-8">
                <AnimatePresence mode="wait">
                    <motion.div 
                        key={currentView}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {currentView === 'dashboard' && renderDashboard()}
                        {currentView === 'catalog' && renderCatalog()}
                        {currentView === 'sales' && renderSales()}
                        {currentView === 'partners' && renderPartners()}
                        {currentView === 'support' && renderSupport()}
                    </motion.div>
                </AnimatePresence>
            </div>
        </div>

        {/* === PARTNER EDIT MODAL === */}
        <AnimatePresence>
            {editingPartner && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setEditingPartner(null)} />
                    <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="relative w-full max-w-lg bg-[#080808] border border-white/20 p-6 shadow-2xl">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-display font-bold text-white">MANAGE PARTNER</h3>
                            <button onClick={() => setEditingPartner(null)}><X size={20} className="text-gray-500" /></button>
                        </div>
                        <div className="space-y-6">
                            <div className="flex items-center gap-4 bg-white/5 p-4 rounded-sm">
                                <div className="w-12 h-12 bg-black border border-white/10 flex items-center justify-center rounded-full"><User size={24} /></div>
                                <div>
                                    <div className="font-bold text-white text-lg">{editingPartner.handle}</div>
                                    <div className="text-xs text-gray-500">ID: #{editingPartner.id}</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-black p-3 border border-white/10">
                                    <label className="text-[9px] text-gray-500 block mb-2">PARTNER LEVEL</label>
                                    <div className="flex items-center gap-2 cursor-pointer" onClick={togglePartnerVip}>
                                        <div className={`w-4 h-4 border border-white/30 flex items-center justify-center ${editingPartner.level === 'ARCHITECT' ? 'bg-pandora-cyan border-pandora-cyan' : ''}`}>
                                            {editingPartner.level === 'ARCHITECT' && <CheckCircle size={10} className="text-black" />}
                                        </div>
                                        <span className={`text-xs font-bold ${editingPartner.level === 'ARCHITECT' ? 'text-pandora-cyan' : 'text-gray-400'}`}>ARCHITECT STATUS</span>
                                    </div>
                                </div>
                                <div className="bg-black p-3 border border-white/10">
                                    <label className="text-[9px] text-gray-500 block mb-2">REWARD TYPE</label>
                                    <div className="flex items-center gap-2 cursor-pointer" onClick={toggleRewardType}>
                                        <div className={`w-8 h-4 rounded-full relative transition-colors ${editingPartner.rewardType === 'commission' ? 'bg-green-500' : 'bg-purple-500'}`}>
                                            <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${editingPartner.rewardType === 'commission' ? 'left-0.5' : 'left-4.5'}`} />
                                        </div>
                                        <span className="text-xs font-bold text-white">{editingPartner.rewardType === 'commission' ? 'CASH' : 'DISCOUNT'}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <button onClick={() => setEditingPartner(null)} className="w-full bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest text-xs">SAVE SETTINGS</button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>

        {/* === PRODUCT / STOCK MODAL === */}
        <AnimatePresence>
            {isProductModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setIsProductModalOpen(false)} />
                    <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="relative w-full max-w-2xl bg-[#080808] border border-white/20 p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-display font-bold text-white">{editingProduct ? `EDIT: ${editingProduct.name}` : 'NEW PRODUCT'}</h3>
                            <button onClick={() => setIsProductModalOpen(false)}><X size={20} className="text-gray-500" /></button>
                        </div>

                        {/* Tabs */}
                        <div className="flex gap-4 border-b border-white/10 mb-6">
                            <button onClick={() => setProductTab('general')} className={`pb-2 text-xs font-bold uppercase ${productTab === 'general' ? 'text-pandora-cyan border-b-2 border-pandora-cyan' : 'text-gray-500'}`}>General Info</button>
                            <button onClick={() => setProductTab('inventory')} className={`pb-2 text-xs font-bold uppercase ${productTab === 'inventory' ? 'text-pandora-cyan border-b-2 border-pandora-cyan' : 'text-gray-500'}`}>Inventory (Stock)</button>
                        </div>

                        {productTab === 'general' ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                
                                {/* --- NEW: MEDIA SECTION --- */}
                                <div className="col-span-1 md:col-span-2 bg-[#050505] p-4 border border-white/10 mb-2">
                                    <h4 className="text-xs font-mono text-gray-500 uppercase mb-3 flex items-center gap-2">
                                        <ImageIcon size={14} /> Media Assets
                                    </h4>
                                    <div className="flex gap-4 items-start">
                                        
                                        {/* Image Upload Area */}
                                        <div className="relative group w-32 h-32 bg-black border border-white/20 flex items-center justify-center cursor-pointer hover:border-pandora-cyan transition-colors" onClick={triggerFileInput}>
                                            {editingProduct?.image ? (
                                                <img src={editingProduct.image} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                            ) : (
                                                <div className="text-center text-gray-500 group-hover:text-pandora-cyan">
                                                    <Upload size={24} className="mx-auto mb-1" />
                                                    <span className="text-[9px] uppercase">Upload</span>
                                                </div>
                                            )}
                                            {/* Hidden File Input */}
                                            <input 
                                                type="file" 
                                                ref={fileInputRef} 
                                                className="hidden" 
                                                accept="image/*"
                                                onChange={handleImageUpload}
                                            />
                                        </div>

                                        {/* Video Input */}
                                        <div className="flex-1 space-y-3">
                                            <div>
                                                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Image URL (Fallback)</label>
                                                <input 
                                                    type="text" 
                                                    value={editingProduct?.image || ''} 
                                                    onChange={(e) => setEditingProduct({...editingProduct, image: e.target.value})}
                                                    className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                                                    placeholder="https://..."
                                                />
                                            </div>
                                            <div>
                                                <label className="text-[10px] text-gray-500 block mb-1 uppercase flex items-center gap-1"><Video size={10} /> Video Instruction URL</label>
                                                <input 
                                                    type="text" 
                                                    value={editingProduct?.video || ''}
                                                    onChange={(e) => setEditingProduct({...editingProduct, video: e.target.value})}
                                                    className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                                                    placeholder="https://youtube.com/..."
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="col-span-1 md:col-span-2">
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Product Name *</label>
                                    <input type="text" defaultValue={editingProduct?.name} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>

                                <div className="col-span-1 md:col-span-2">
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Description</label>
                                    <textarea defaultValue={editingProduct?.description} className="w-full h-20 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none" placeholder="Short description..." />
                                </div>

                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Price (₽) *</label>
                                    <input type="number" defaultValue={editingProduct?.price} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>
                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">MSRP (Strike Price)</label>
                                    <input type="number" defaultValue={editingProduct?.msrp} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>

                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Type</label>
                                    <select className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none">
                                        <option>Instant Delivery</option>
                                        <option>Pre-order</option>
                                        <option>Manual</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Stock (Manual)</label>
                                    <input type="number" defaultValue={editingProduct?.stock || 0} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>

                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Category</label>
                                    <select defaultValue={editingProduct?.category || "Text"} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none">
                                        <option>Text</option>
                                        <option>Video</option>
                                        <option>Image</option>
                                        <option>Code</option>
                                        <option>Audio</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-2 border border-white/20 p-2 bg-black">
                                    <input type="checkbox" defaultChecked={editingProduct?.vpn} className="accent-pandora-cyan w-4 h-4" />
                                    <label className="text-xs text-white uppercase font-bold">VPN Required</label>
                                </div>

                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Fulfillment (Hours)</label>
                                    <input type="number" defaultValue={editingProduct?.fulfillment || 0} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>
                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Warranty (Hours)</label>
                                    <input type="number" defaultValue={editingProduct?.warranty || 24} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>
                                <div>
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Duration (Days)</label>
                                    <input type="number" defaultValue={editingProduct?.duration || 30} className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" />
                                </div>

                                <div className="col-span-1 md:col-span-2">
                                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Access Instructions</label>
                                    <textarea defaultValue={editingProduct?.instructions} className="w-full h-24 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none" placeholder="1. Download..." />
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="bg-[#050505] p-4 border border-green-500/20 rounded-sm">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-xs font-mono text-green-500 flex items-center gap-2"><Terminal size={12} /> BULK KEY UPLOAD</span>
                                        <span className="text-[10px] text-gray-500">{inventoryText.split('\n').filter(l => l.trim()).length} ITEMS DETECTED</span>
                                    </div>
                                    <textarea 
                                        value={inventoryText}
                                        onChange={(e) => setInventoryText(e.target.value)}
                                        placeholder={`Paste keys here, one per line:\nuser:pass\napi_key_1\napi_key_2`}
                                        className="w-full h-48 bg-black border border-white/10 p-3 text-xs font-mono text-green-400 focus:border-green-500/50 outline-none resize-none"
                                    />
                                </div>
                                <div className="flex justify-end">
                                    <button 
                                        onClick={handleStockUpdate}
                                        className="bg-green-600 hover:bg-green-500 text-black font-bold py-2 px-6 text-xs uppercase flex items-center gap-2"
                                    >
                                        <Plus size={14} /> Parse & Add to Stock
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="mt-8 pt-4 border-t border-white/10 flex justify-end gap-3">
                            <button onClick={() => setIsProductModalOpen(false)} className="px-4 py-2 border border-white/10 text-xs font-bold text-gray-400 hover:text-white">CANCEL</button>
                            <button className="px-4 py-2 bg-pandora-cyan text-black text-xs font-bold hover:bg-white flex items-center gap-2"><Save size={14} /> SAVE PRODUCT</button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>

    </motion.div>
  );
};

// --- SUB COMPONENTS ---

const AdminNavItem: React.FC<{ icon: React.ReactNode, label: string, active: boolean, onClick: () => void, collapsed: boolean }> = ({ icon, label, active, onClick, collapsed }) => (
    <button 
        onClick={onClick}
        className={`flex items-center gap-3 w-full p-3 rounded-sm transition-all relative group ${active ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-white hover:bg-white/5'} ${collapsed ? 'justify-center' : ''}`}
    >
        {active && <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500 rounded-l-sm" />}
        {icon}
        {!collapsed && <span className="text-xs font-bold uppercase tracking-wide">{label}</span>}
    </button>
);

const StatCard: React.FC<{ label: string, value: string, trend: string, icon: React.ReactNode, isNegative?: boolean }> = ({ label, value, trend, icon, isNegative = false }) => (
    <div className="bg-[#0e0e0e] border border-white/10 p-4 md:p-6 rounded-sm hover:border-white/20 transition-colors">
        <div className="flex justify-between items-start mb-2">
            <div className="text-[10px] text-gray-500 font-mono uppercase">{label}</div>
            <div className="text-gray-600">{icon}</div>
        </div>
        <div className="text-xl md:text-2xl font-bold text-white mb-2">{value}</div>
        <div className={`text-xs font-bold ${isNegative ? 'text-red-500' : 'text-green-500'} flex items-center gap-1`}>
            {isNegative ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
            {trend} <span className="text-gray-600 font-normal hidden md:inline">vs last week</span>
        </div>
    </div>
);

const StockIndicator: React.FC<{ stock: number }> = ({ stock }) => (
    <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${stock > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className={`text-xs font-mono ${stock > 0 ? 'text-white' : 'text-red-500'}`}>{stock} units</span>
    </div>
);

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const getColor = (s: string) => {
        switch(s.toUpperCase()) {
            case 'PAID': case 'ACTIVE': case 'OPEN': return 'text-green-500 bg-green-500/10 border-green-500/20';
            case 'REFUNDED': case 'INACTIVE': case 'CLOSED': return 'text-red-500 bg-red-500/10 border-red-500/20';
            case 'VIP': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
            default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
        }
    }
    return (
        <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${getColor(status)}`}>
            {status.toUpperCase()}
        </span>
    );
};

export default AdminPanel;
