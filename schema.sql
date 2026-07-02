-- =============================================
-- BOT IA ENTERPRISE - MYSQL 8.0+
-- Base de datos multi-tenant para WhatsApp Bot
-- =============================================

CREATE DATABASE IF NOT EXISTS bot_enterprise;
USE bot_enterprise;

-- =============================================
-- 1. TENANTS (Empresas)
-- =============================================
CREATE TABLE tenants (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    business_name VARCHAR(255) NOT NULL,
    commercial_name VARCHAR(255),
    rut VARCHAR(20) UNIQUE,
    phone_number VARCHAR(20) UNIQUE NOT NULL COMMENT 'Número WhatsApp Business',
    email VARCHAR(255) UNIQUE NOT NULL,
    
    -- Configuración del Bot
    system_prompt TEXT NOT NULL COMMENT 'Personalidad y reglas del bot',
    welcome_message TEXT,
    bot_temperature DECIMAL(3,2) DEFAULT 0.70,
    bot_model VARCHAR(50) DEFAULT 'llama3-70b-8192',
    bot_is_active BOOLEAN DEFAULT TRUE,
    
    -- Datos de pago (JSON)
    payment_info JSON NOT NULL DEFAULT (JSON_OBJECT(
        'bank', '',
        'account_number', '',
        'account_type', '',
        'owner_name', '',
        'owner_ci', '',
        'phone', '',
        'instructions', ''
    )),
    
    -- Plan y límites
    plan VARCHAR(50) DEFAULT 'free',
    monthly_message_limit INT DEFAULT 100,
    products_limit INT DEFAULT 50,
    
    -- Metadata
    settings JSON DEFAULT (JSON_OBJECT()),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_phone (phone_number),
    INDEX idx_email (email),
    INDEX idx_plan (plan)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 2. TENANT_USERS (Administradores)
-- =============================================
CREATE TABLE tenant_users (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role ENUM('super_admin', 'admin', 'viewer') DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE KEY unique_tenant_email (tenant_id, email),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 3. CLIENTS (Clientes de las empresas)
-- CI como identificador manual obligatorio
-- =============================================
CREATE TABLE clients (
    tenant_id CHAR(36) NOT NULL,
    ci VARCHAR(20) NOT NULL COMMENT 'Cédula de Identidad (manual/obligatorio)',
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    delivery_address TEXT,
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    
    -- Metadatos
    tags JSON DEFAULT (JSON_ARRAY()),
    notes TEXT,
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    last_order_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (tenant_id, ci),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_phone (phone),
    INDEX idx_full_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 4. CATEGORIES (Categorías por tenant)
-- =============================================
CREATE TABLE categories (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id CHAR(36) NULL,
    icon_url VARCHAR(500),
    image_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_tenant_active (tenant_id, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 5. PRODUCTS (Catálogo agnóstico con JSON)
-- =============================================
CREATE TABLE products (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    category_id CHAR(36) NULL,
    
    -- Campos base
    sku VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    compare_at_price DECIMAL(12,2) COMMENT 'Precio anterior (para ofertas)',
    cost DECIMAL(12,2) DEFAULT 0.00,
    stock INT DEFAULT 0,
    stock_status ENUM('in_stock', 'low_stock', 'out_of_stock') DEFAULT 'in_stock',
    
    -- Multimedia
    image_url VARCHAR(500),
    gallery_urls JSON DEFAULT (JSON_ARRAY()),
    
    -- Campos flexibles (JSON para atributos variables)
    attributes JSON DEFAULT (JSON_OBJECT()),
    
    -- SEO y visibilidad
    tags JSON DEFAULT (JSON_ARRAY()),
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    weight INT DEFAULT 0 COMMENT 'Orden de visualización',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_tenant_active (tenant_id, is_active),
    INDEX idx_name (name),
    FULLTEXT idx_search (name, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 6. ORDERS (Pedidos)
-- =============================================
CREATE TABLE orders (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    client_ci VARCHAR(20) NOT NULL,
    
    -- Montos (calculados en backend, NO por IA)
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    tax DECIMAL(12,2) DEFAULT 0.00,
    delivery_fee DECIMAL(12,2) DEFAULT 0.00,
    discount DECIMAL(12,2) DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    
    -- Estado del pedido
    status ENUM('pending', 'confirmed', 'paid', 'preparing', 'ready', 'delivered', 'cancelled') DEFAULT 'pending',
    payment_method ENUM('movil', 'transferencia', 'efectivo', 'tarjeta', 'mercadopago') NULL,
    payment_status ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
    payment_receipt_url VARCHAR(500) COMMENT 'URL de la captura de pago',
    
    -- Entrega
    delivery_address TEXT,
    delivery_lat DECIMAL(10,8),
    delivery_lng DECIMAL(11,8),
    scheduled_for TIMESTAMP NULL,
    
    -- Notas
    client_notes TEXT,
    internal_notes TEXT,
    
    -- Metadatos
    channel VARCHAR(20) DEFAULT 'whatsapp',
    metadata JSON DEFAULT (JSON_OBJECT()),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, client_ci) REFERENCES clients(tenant_id, ci),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_created_at (created_at),
    INDEX idx_client (tenant_id, client_ci)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 7. ORDER_ITEMS (Detalles del pedido)
-- =============================================
CREATE TABLE order_items (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_id CHAR(36) NOT NULL,
    product_id CHAR(36) NOT NULL,
    
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(12,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    
    -- Variantes seleccionadas
    selected_options JSON DEFAULT (JSON_OBJECT()),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 8. CONVERSATIONS (Conversaciones)
-- =============================================
CREATE TABLE conversations (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    client_ci VARCHAR(20) NOT NULL,
    channel VARCHAR(20) DEFAULT 'whatsapp',
    
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    message_count INT DEFAULT 0,
    
    -- Contexto actual
    current_intent VARCHAR(100) COMMENT 'purchase, inquiry, complaint, support',
    current_order_id CHAR(36) NULL,
    conversation_state JSON DEFAULT (JSON_OBJECT()) COMMENT '{"step": "asking_ci", "cart": {...}}',
    
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP NULL,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, client_ci) REFERENCES clients(tenant_id, ci),
    FOREIGN KEY (current_order_id) REFERENCES orders(id),
    INDEX idx_tenant_active (tenant_id, last_activity DESC),
    INDEX idx_client (tenant_id, client_ci)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 9. MESSAGES (Mensajes individuales)
-- =============================================
CREATE TABLE messages (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    conversation_id CHAR(36) NOT NULL,
    
    role ENUM('user', 'assistant', 'system') NOT NULL,
    content TEXT NOT NULL,
    content_type ENUM('text', 'image', 'audio', 'document') DEFAULT 'text',
    
    -- Multimedia
    media_url VARCHAR(500),
    media_mime_type VARCHAR(100),
    
    -- IA Metrics
    intent_detected VARCHAR(100),
    tokens_used INT,
    processing_time_ms INT,
    cost_usd DECIMAL(10,6),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation (conversation_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 10. RAG_DOCUMENTS (Para búsqueda semántica)
-- =============================================
CREATE TABLE rag_documents (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    entity_type ENUM('product', 'category', 'faq') NOT NULL,
    entity_id CHAR(36) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INT DEFAULT 0,
    keywords TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant_entity (tenant_id, entity_type, entity_id),
    FULLTEXT idx_search (chunk_text, keywords)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 11. USAGE_LOGS (Métricas para facturación)
-- =============================================
CREATE TABLE usage_logs (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    
    message_id CHAR(36) NULL,
    message_type ENUM('text', 'audio', 'image') DEFAULT 'text',
    model_used VARCHAR(50),
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0.00,
    processing_time_ms INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant_date (tenant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 12. WEBHOOK_LOGS (Depuración)
-- =============================================
CREATE TABLE webhook_logs (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NULL,
    
    endpoint VARCHAR(255),
    method VARCHAR(10),
    request_headers JSON,
    request_body JSON,
    response_status INT,
    response_body TEXT,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_created (created_at DESC),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 13. SUBSCRIPTION_PLANS
-- =============================================
CREATE TABLE subscription_plans (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(50) NOT NULL,
    price_monthly DECIMAL(10,2) NOT NULL,
    price_yearly DECIMAL(10,2) NOT NULL,
    conversations_limit INT NOT NULL,
    products_limit INT NOT NULL,
    agents_limit INT DEFAULT 1,
    features JSON NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar planes por defecto
INSERT INTO subscription_plans (id, name, price_monthly, price_yearly, conversations_limit, products_limit, agents_limit, features) VALUES
(UUID(), 'Free', 0, 0, 100, 20, 1, '{"whatsapp": true, "web_chat": true, "basic_analytics": true, "support": "email"}'),
(UUID(), 'Startup', 49, 499, 1000, 200, 1, '{"whatsapp": true, "web_chat": true, "basic_analytics": true, "support": "email", "api_access": true}'),
(UUID(), 'Business', 199, 1999, 5000, 1000, 3, '{"whatsapp": true, "web_chat": true, "advanced_analytics": true, "support": "priority", "api_access": true, "multiple_agents": true}'),
(UUID(), 'Enterprise', 499, 4999, 999999, 999999, 10, '{"whatsapp": true, "web_chat": true, "custom_analytics": true, "support": "dedicated", "api_access": true, "white_label": true, "custom_integrations": true}');

-- =============================================
-- 14. TENANT_SUBSCRIPTIONS
-- =============================================
CREATE TABLE tenant_subscriptions (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    tenant_id CHAR(36) NOT NULL,
    plan_id CHAR(36) NOT NULL,
    
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    auto_renew BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id),
    INDEX idx_tenant_active (tenant_id, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- TRIGGERS
-- =============================================

-- Actualizar stats del cliente cuando se crea un pedido
DELIMITER //
CREATE TRIGGER update_client_stats
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    UPDATE clients 
    SET 
        total_orders = total_orders + 1,
        total_spent = total_spent + NEW.total_amount,
        last_order_at = NOW()
    WHERE tenant_id = NEW.tenant_id AND ci = NEW.client_ci;
END//
DELIMITER ;

-- Actualizar stock de productos
DELIMITER //
CREATE TRIGGER update_product_stock
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE products 
    SET stock = stock - NEW.quantity
    WHERE id = NEW.product_id;
END//
DELIMITER ;

-- =============================================
-- VISTAS ÚTILES
-- =============================================

CREATE VIEW daily_sales AS
SELECT 
    tenant_id,
    DATE(created_at) as sale_date,
    COUNT(*) as total_orders,
    SUM(total_amount) as total_sales,
    AVG(total_amount) as avg_order_value
FROM orders
WHERE status IN ('delivered', 'paid')
GROUP BY tenant_id, DATE(created_at);

CREATE VIEW bot_performance AS
SELECT 
    tenant_id,
    DATE(created_at) as date,
    COUNT(*) as total_messages,
    AVG(processing_time_ms) as avg_response_time,
    AVG(cost_usd) as avg_cost
FROM messages
WHERE role = 'assistant'
GROUP BY tenant_id, DATE(created_at);
