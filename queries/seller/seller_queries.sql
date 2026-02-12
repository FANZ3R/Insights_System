-- @name: performance_overview
-- @description: Sales, customers, and repeat purchase metrics

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

order_level AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        pi.po_id,
        SUM(pi.total_amount) AS order_total,
        SUM(pi.qty) AS total_qty
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, pi.po_id
),

sales_metrics AS (
    SELECT 
        vendor_id,
        ROUND(SUM(order_total)::numeric, 2) AS total_sales,
        ROUND(SUM(total_qty)::numeric, 2) AS units_sold,
        ROUND(SUM(order_total)::numeric / NULLIF(COUNT(po_id), 0), 2) AS average_order_value
    FROM order_level
    GROUP BY vendor_id
),

base_orders AS (
    SELECT DISTINCT
        pd.seller_org_id AS vendor_id,
        pd.buyer_org_id AS buyer_id,
        pd.id AS po_id
    FROM po_details pd
    JOIN po_items pi ON pd.id = pi.po_id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pd.created_date BETWEEN p.start_date AND p.end_date
      AND pd.buyer_org_id IS NOT NULL
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
),

buyer_order_counts AS (
    SELECT 
        vendor_id,
        buyer_id,
        COUNT(DISTINCT po_id) AS order_count
    FROM base_orders
    GROUP BY vendor_id, buyer_id
),

repeat_purchase_metrics AS (
    SELECT
        vendor_id,
        COUNT(DISTINCT buyer_id) AS total_buyers,
        COUNT(DISTINCT CASE WHEN order_count > 1 THEN buyer_id END) AS repeat_buyers,
        ROUND(
            (COUNT(DISTINCT CASE WHEN order_count > 1 THEN buyer_id END)::numeric 
             / NULLIF(COUNT(DISTINCT buyer_id), 0)) * 100, 
            2
        ) AS repeat_purchase_rate_pct
    FROM buyer_order_counts
    GROUP BY vendor_id
)

SELECT 
    sm.vendor_id,
    sm.total_sales,
    sm.units_sold,
    sm.average_order_value,
    COALESCE(rpm.total_buyers, 0) AS total_buyers,
    COALESCE(rpm.repeat_buyers, 0) AS repeat_buyers,
    COALESCE(rpm.repeat_purchase_rate_pct, 0) AS repeat_purchase_rate_pct
FROM sales_metrics sm
LEFT JOIN repeat_purchase_metrics rpm ON sm.vendor_id = rpm.vendor_id
ORDER BY sm.vendor_id;

-- @name: monthly_trends
-- @description: Month-over-month sales trends

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

active_vendors AS (
    SELECT DISTINCT pd.seller_org_id AS vendor_id
    FROM po_details pd
    JOIN po_items pi ON pd.id = pi.po_id
    CROSS JOIN params p
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
),

month_series AS (
    SELECT generate_series(
        date_trunc('month', (SELECT start_date FROM params)),
        date_trunc('month', (SELECT end_date FROM params)),
        interval '1 month'
    ) AS month
),

vendor_months AS (
    SELECT 
        av.vendor_id,
        ms.month
    FROM active_vendors av
    CROSS JOIN month_series ms
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

monthly_sales AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        date_trunc('month', pi.created_date) AS month,
        SUM(pi.total_amount) AS total_sales,
        SUM(pi.qty) AS total_units,
        COUNT(DISTINCT pi.po_id) AS order_count
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, date_trunc('month', pi.created_date)
)

SELECT
    vm.vendor_id,
    TO_CHAR(vm.month, 'YYYY-MM') AS month,
    COALESCE(ROUND(msl.total_sales::numeric, 2), 0) AS total_sales,
    COALESCE(ROUND(msl.total_units::numeric, 2), 0) AS total_units,
    COALESCE(msl.order_count, 0) AS order_count,
    COALESCE(ROUND(LAG(msl.total_sales) OVER (
        PARTITION BY vm.vendor_id 
        ORDER BY vm.month
    )::numeric, 2), 0) AS prev_month_sales,
    CASE
        WHEN LAG(msl.total_sales) OVER (
            PARTITION BY vm.vendor_id 
            ORDER BY vm.month
        ) IS NULL 
            OR LAG(msl.total_sales) OVER (
                PARTITION BY vm.vendor_id 
                ORDER BY vm.month
            ) = 0 
        THEN NULL
        ELSE ROUND(
            (((COALESCE(msl.total_sales, 0) - LAG(msl.total_sales) OVER (
                PARTITION BY vm.vendor_id 
                ORDER BY vm.month
            ))
              / NULLIF(LAG(msl.total_sales) OVER (
                  PARTITION BY vm.vendor_id 
                  ORDER BY vm.month
              ), 0)) * 100)::numeric,
            2
        )
    END AS mom_growth_rate_pct
FROM vendor_months vm
LEFT JOIN monthly_sales msl ON vm.vendor_id = msl.vendor_id AND vm.month = msl.month
ORDER BY vm.vendor_id, vm.month;

-- @name: quarterly_trends
-- @description: Quarter-over-quarter sales trends

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

active_vendors AS (
    SELECT DISTINCT pd.seller_org_id AS vendor_id
    FROM po_details pd
    JOIN po_items pi ON pd.id = pi.po_id
    CROSS JOIN params p
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
),

quarter_series AS (
    SELECT generate_series(
        date_trunc('quarter', (SELECT start_date FROM params)),
        date_trunc('quarter', (SELECT end_date FROM params)),
        interval '3 month'
    ) AS quarter_start
),

vendor_quarters AS (
    SELECT 
        av.vendor_id,
        qs.quarter_start
    FROM active_vendors av
    CROSS JOIN quarter_series qs
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

quarterly_sales AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        date_trunc('quarter', pi.created_date) AS quarter_start,
        SUM(pi.total_amount) AS total_sales,
        SUM(pi.qty) AS total_units,
        COUNT(DISTINCT pi.po_id) AS order_count
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, date_trunc('quarter', pi.created_date)
)

SELECT
    vq.vendor_id,
    TO_CHAR(vq.quarter_start, '"Q"Q YYYY') AS quarter,
    vq.quarter_start,
    COALESCE(ROUND(qsl.total_sales::numeric, 2), 0) AS total_sales,
    COALESCE(ROUND(qsl.total_units::numeric, 2), 0) AS total_units,
    COALESCE(qsl.order_count, 0) AS order_count,
    COALESCE(ROUND(LAG(qsl.total_sales) OVER (
        PARTITION BY vq.vendor_id 
        ORDER BY vq.quarter_start
    )::numeric, 2), 0) AS prev_quarter_sales,
    CASE
        WHEN LAG(qsl.total_sales) OVER (
            PARTITION BY vq.vendor_id 
            ORDER BY vq.quarter_start
        ) IS NULL 
            OR LAG(qsl.total_sales) OVER (
                PARTITION BY vq.vendor_id 
                ORDER BY vq.quarter_start
            ) = 0 
        THEN NULL
        ELSE ROUND(
            (((COALESCE(qsl.total_sales, 0) - LAG(qsl.total_sales) OVER (
                PARTITION BY vq.vendor_id 
                ORDER BY vq.quarter_start
            ))
              / NULLIF(LAG(qsl.total_sales) OVER (
                  PARTITION BY vq.vendor_id 
                  ORDER BY vq.quarter_start
              ), 0)) * 100)::numeric,
            2
        )
    END AS qoq_growth_rate_pct
FROM vendor_quarters vq
LEFT JOIN quarterly_sales qsl ON vq.vendor_id = qsl.vendor_id 
                              AND vq.quarter_start = qsl.quarter_start
ORDER BY vq.vendor_id, vq.quarter_start;

-- @name: product_line_breakdown
-- @description: Revenue contribution by product category

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

base_sales AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        pi.product_id,
        pi.total_amount,
        pi.qty
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
),

sales_with_category AS (
    SELECT 
        b.vendor_id,
        COALESCE(pc.category_name, 'Unknown') AS category_name,
        b.total_amount,
        b.qty
    FROM base_sales b
    LEFT JOIN product_categories pc ON b.product_id = pc.product_id
),

category_sales AS (
    SELECT 
        vendor_id,
        category_name,
        ROUND(SUM(total_amount)::numeric, 2) AS total_revenue,
        ROUND(SUM(qty)::numeric, 2) AS total_units,
        COUNT(*) AS transaction_count
    FROM sales_with_category
    GROUP BY vendor_id, category_name
),

vendor_total AS (
    SELECT 
        vendor_id,
        SUM(total_revenue) AS vendor_total_revenue
    FROM category_sales
    GROUP BY vendor_id
)

SELECT 
    cs.vendor_id,
    cs.category_name AS product_line,
    cs.total_revenue,
    cs.total_units,
    cs.transaction_count,
    ROUND((cs.total_revenue / NULLIF(vt.vendor_total_revenue, 0)) * 100, 2) AS revenue_contribution_pct
FROM category_sales cs
JOIN vendor_total vt ON cs.vendor_id = vt.vendor_id
ORDER BY cs.vendor_id, cs.total_revenue DESC;

-- @name: sales_time_series
-- @description: Sales by configurable time period (day/week/month)

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        %(time_resolution)s::TEXT AS time_resolution,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

sales_time AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        date_trunc((SELECT time_resolution FROM params), pi.created_date) AS date_period,
        SUM(pi.total_amount) AS total_sales,
        SUM(pi.qty) AS total_units,
        COUNT(DISTINCT pi.po_id) AS order_count
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, date_trunc((SELECT time_resolution FROM params), pi.created_date)
)

SELECT 
    vendor_id,
    CASE 
        WHEN (SELECT time_resolution FROM params) = 'day' 
            THEN TO_CHAR(date_period, 'YYYY-MM-DD')
        WHEN (SELECT time_resolution FROM params) = 'week' 
            THEN TO_CHAR(date_period, 'YYYY-MM-DD') || ' (Week ' || TO_CHAR(date_period, 'IW') || ')'
        WHEN (SELECT time_resolution FROM params) = 'month' 
            THEN TO_CHAR(date_period, 'YYYY-MM')
    END AS period_label,
    date_period,
    ROUND(total_sales::numeric, 2) AS total_sales,
    ROUND(total_units::numeric, 2) AS total_units,
    order_count,
    ROUND((total_sales / NULLIF(order_count, 0))::numeric, 2) AS avg_order_value
FROM sales_time
ORDER BY vendor_id, date_period;

-- @name: top_selling_products
-- @description: Top selling products by revenue

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        %(top_n)s AS top_n_products,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

product_sales AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        pi.product_id,
        SUM(pi.total_amount) AS total_revenue,
        SUM(pi.qty) AS total_units,
        COUNT(DISTINCT pi.po_id) AS order_count,
        COUNT(*) AS line_item_count,
        ROW_NUMBER() OVER (
            PARTITION BY pd.seller_org_id 
            ORDER BY SUM(pi.total_amount) DESC
        ) AS rank_within_vendor
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, pi.product_id
)

SELECT 
    ps.vendor_id,
    vp.product_name,
    COALESCE(pc.category_name, 'Unknown') AS category,
    ROUND(ps.total_revenue::numeric, 2) AS total_revenue,
    ROUND(ps.total_units::numeric, 2) AS total_units,
    ps.order_count,
    ps.line_item_count,
    ROUND((ps.total_revenue / NULLIF(ps.total_units, 0))::numeric, 2) AS avg_price_per_unit,
    ps.rank_within_vendor
FROM product_sales ps
JOIN vendor_products vp ON ps.product_id = vp.id
LEFT JOIN product_categories pc ON ps.product_id = pc.product_id
WHERE ps.rank_within_vendor <= (SELECT top_n_products FROM params)
ORDER BY ps.vendor_id, ps.rank_within_vendor;

-- @name: regional_distribution
-- @description: Sales distribution by geographic region

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

regional_sales AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        COALESCE(ua.city, 'Unknown') AS region,
        SUM(pi.total_amount) AS total_revenue,
        SUM(pi.qty) AS total_units,
        COUNT(DISTINCT pi.po_id) AS order_count
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    LEFT JOIN user_address ua ON pd.shipping_address = ua.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, ua.city
),

total_revenue AS (
    SELECT 
        vendor_id,
        SUM(total_revenue) AS vendor_total_revenue
    FROM regional_sales
    GROUP BY vendor_id
)

SELECT 
    rs.vendor_id,
    rs.region,
    ROUND(rs.total_revenue::numeric, 2) AS total_revenue,
    ROUND(rs.total_units::numeric, 2) AS total_units,
    rs.order_count,
    ROUND((rs.total_revenue / NULLIF(tr.vendor_total_revenue, 0) * 100)::numeric, 2) AS revenue_contribution_pct
FROM regional_sales rs
JOIN total_revenue tr ON rs.vendor_id = tr.vendor_id
ORDER BY rs.vendor_id, rs.total_revenue DESC;

-- @name: order_analysis
-- @description: Order value vs quantity analysis

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        NULL::TEXT[] AS category_filter,
        NULL::TEXT[] AS channel_filter
),

product_categories AS (
    SELECT
        vp.id AS product_id,
        (
            SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category_name
    FROM vendor_products vp
),

order_data AS (
    SELECT 
        pd.seller_org_id AS vendor_id,
        pi.po_id,
        pd.created_date,
        COALESCE(pd.source, 'Unknown') AS sales_channel,
        SUM(pi.total_amount) AS order_value,
        SUM(pi.qty) AS total_quantity
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    LEFT JOIN product_categories pc ON pi.product_id = pc.product_id
    WHERE pi.created_date BETWEEN p.start_date AND p.end_date
      AND (p.category_filter IS NULL OR pc.category_name = ANY(p.category_filter))
      AND (p.channel_filter IS NULL OR pd.source = ANY(p.channel_filter))
    GROUP BY pd.seller_org_id, pi.po_id, pd.created_date, pd.source
)

SELECT 
    od.vendor_id,
    od.po_id,
    ROUND(od.order_value::numeric, 2) AS order_value,
    ROUND(od.total_quantity::numeric, 2) AS quantity,
    od.sales_channel,
    TO_CHAR(od.created_date, 'YYYY-MM-DD') AS order_date,
    ROUND((od.order_value / NULLIF(od.total_quantity, 0))::numeric, 2) AS avg_price_per_unit
FROM order_data od
ORDER BY od.vendor_id, od.order_value DESC;