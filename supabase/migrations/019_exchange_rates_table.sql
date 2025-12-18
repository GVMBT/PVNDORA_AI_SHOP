-- Exchange rates table - stores real-time currency rates
-- Updated via cron job, read in runtime (no external API dependency)

CREATE TABLE IF NOT EXISTS exchange_rates (
    currency VARCHAR(3) PRIMARY KEY,
    rate NUMERIC(12, 6) NOT NULL,  -- Rate relative to USD (1 USD = X currency)
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initial rates (will be updated by cron)
INSERT INTO exchange_rates (currency, rate) VALUES
    ('USD', 1.000000),
    ('RUB', 80.000000),
    ('EUR', 0.920000),
    ('UAH', 41.000000),
    ('TRY', 34.000000),
    ('INR', 84.000000),
    ('AED', 3.670000),
    ('GBP', 0.790000),
    ('CNY', 7.250000),
    ('JPY', 154.000000),
    ('KRW', 1400.000000),
    ('BRL', 6.100000)
ON CONFLICT (currency) DO NOTHING;

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currency ON exchange_rates(currency);

-- Comment
COMMENT ON TABLE exchange_rates IS 'Currency exchange rates (1 USD = X currency). Updated hourly via cron.';

