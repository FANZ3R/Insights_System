-- @name: overview_metrics
-- @description: Period-over-period comparison of buyer metrics

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date
),

date_params AS (
    SELECT
        start_date,
        end_date,
        start_date - (end_date - start_date + 1) AS prev_start_date,
        start_date - 1 AS prev_end_date
    FROM params
),

po_data AS (
    SELECT
        pd.buyer_org_id,
        pi.product_id,
        pi.total_amount,
        pi.qty,
        pi.updated_date,
        pd.seller_org_id,
        CASE 
            WHEN pi.updated_date BETWEEN (SELECT start_date FROM date_params) 
                                     AND (SELECT end_date FROM date_params)
            THEN 'current'
            WHEN pi.updated_date BETWEEN (SELECT prev_start_date FROM date_params) 
                                     AND (SELECT prev_end_date FROM date_params)
            THEN 'previous'
        END AS period
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN date_params dp
    WHERE pi.updated_date BETWEEN (SELECT prev_start_date FROM date_params) 
                              AND (SELECT end_date FROM date_params)
),

period_metrics AS (
    SELECT
        buyer_org_id,
        SUM(CASE WHEN period = 'current' THEN total_amount ELSE 0 END) AS curr_amount,
        SUM(CASE WHEN period = 'current' THEN qty ELSE 0 END) AS curr_qty,
        COUNT(DISTINCT CASE WHEN period = 'current' THEN seller_org_id END) AS curr_suppliers,
        COUNT(DISTINCT CASE WHEN period = 'current' THEN product_id END) AS curr_items,
        
        SUM(CASE WHEN period = 'previous' THEN total_amount ELSE 0 END) AS prev_amount,
        SUM(CASE WHEN period = 'previous' THEN qty ELSE 0 END) AS prev_qty,
        COUNT(DISTINCT CASE WHEN period = 'previous' THEN seller_org_id END) AS prev_suppliers,
        COUNT(DISTINCT CASE WHEN period = 'previous' THEN product_id END) AS prev_items
    FROM po_data
    GROUP BY buyer_org_id
),

new_items_calc AS (
    SELECT
        pd.buyer_org_id,
        pi.product_id,
        MIN(pi.updated_date) AS first_seen_date
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    GROUP BY pd.buyer_org_id, pi.product_id
),

new_items_agg AS (
    SELECT
        buyer_org_id,
        COUNT(DISTINCT CASE 
            WHEN first_seen_date BETWEEN (SELECT start_date FROM date_params) 
                                     AND (SELECT end_date FROM date_params)
            THEN product_id 
        END) AS new_items_current,
        COUNT(DISTINCT CASE 
            WHEN first_seen_date BETWEEN (SELECT prev_start_date FROM date_params) 
                                     AND (SELECT prev_end_date FROM date_params)
            THEN product_id 
        END) AS new_items_previous
    FROM new_items_calc
    GROUP BY buyer_org_id
),

new_suppliers_calc AS (
    SELECT
        pd.buyer_org_id,
        pd.seller_org_id,
        MIN(pi.updated_date) AS first_seen_date
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    GROUP BY pd.buyer_org_id, pd.seller_org_id
),

new_suppliers_agg AS (
    SELECT
        buyer_org_id,
        COUNT(DISTINCT CASE 
            WHEN first_seen_date BETWEEN (SELECT start_date FROM date_params) 
                                     AND (SELECT end_date FROM date_params)
            THEN seller_org_id 
        END) AS new_suppliers_current,
        COUNT(DISTINCT CASE 
            WHEN first_seen_date BETWEEN (SELECT prev_start_date FROM date_params) 
                                     AND (SELECT prev_end_date FROM date_params)
            THEN seller_org_id 
        END) AS new_suppliers_previous
    FROM new_suppliers_calc
    GROUP BY buyer_org_id
)

SELECT
    pm.buyer_org_id,
    
    pm.curr_amount AS current_period_purchases,
    pm.prev_amount AS previous_period_purchases,
    ROUND(((pm.curr_amount::numeric - pm.prev_amount::numeric) * 100.0 / NULLIF(pm.prev_amount, 0))::numeric, 2) 
        AS purchase_percentage_change,

    pm.curr_qty AS current_period_quantity,
    pm.prev_qty AS previous_period_quantity,
    ROUND(((pm.curr_qty::numeric - pm.prev_qty::numeric) * 100.0 / NULLIF(pm.prev_qty, 0))::numeric, 2) 
        AS quantity_percentage_change,

    ROUND((pm.curr_amount::numeric / NULLIF(pm.curr_suppliers, 0))::numeric, 2) 
        AS avg_purchase_per_supplier_current,
    ROUND((pm.prev_amount::numeric / NULLIF(pm.prev_suppliers, 0))::numeric, 2) 
        AS avg_purchase_per_supplier_previous,
    ROUND(
        (((pm.curr_amount::numeric / NULLIF(pm.curr_suppliers, 0)) - 
         (pm.prev_amount::numeric / NULLIF(pm.prev_suppliers, 0))) * 100.0 / 
        NULLIF((pm.prev_amount::numeric / NULLIF(pm.prev_suppliers, 0)), 0))::numeric, 2
    ) AS avg_purchase_per_supplier_percentage_change,

    ROUND((pm.curr_amount::numeric / NULLIF(pm.curr_qty, 0))::numeric, 2) 
        AS avg_price_per_unit_current,
    ROUND((pm.prev_amount::numeric / NULLIF(pm.prev_qty, 0))::numeric, 2) 
        AS avg_price_per_unit_previous,
    ROUND(
        (((pm.curr_amount::numeric / NULLIF(pm.curr_qty, 0)) - 
         (pm.prev_amount::numeric / NULLIF(pm.prev_qty, 0))) * 100.0 / 
        NULLIF((pm.prev_amount::numeric / NULLIF(pm.prev_qty, 0)), 0))::numeric, 2
    ) AS avg_price_per_unit_percentage_change,

    pm.curr_items AS items_purchased_current,
    pm.prev_items AS items_purchased_previous,
    ROUND(((pm.curr_items::numeric - pm.prev_items::numeric) * 100.0 / NULLIF(pm.prev_items, 0))::numeric, 2) 
        AS items_purchased_percentage_change,

    COALESCE(ni.new_items_current, 0) AS new_items_purchased_current,
    COALESCE(ni.new_items_previous, 0) AS new_items_purchased_previous,

    pm.curr_suppliers AS suppliers_current,
    pm.prev_suppliers AS suppliers_previous,
    ROUND(((pm.curr_suppliers::numeric - pm.prev_suppliers::numeric) * 100.0 / NULLIF(pm.prev_suppliers, 0))::numeric, 2) 
        AS suppliers_percentage_change,

    COALESCE(ns.new_suppliers_current, 0) AS new_suppliers_current,
    COALESCE(ns.new_suppliers_previous, 0) AS new_suppliers_previous

FROM period_metrics pm
LEFT JOIN new_items_agg ni ON pm.buyer_org_id = ni.buyer_org_id
LEFT JOIN new_suppliers_agg ns ON pm.buyer_org_id = ns.buyer_org_id
ORDER BY pm.buyer_org_id;

-- @name: top_products
-- @description: Top products by purchase amount

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        %(top_n)s AS top_n
),

product_rankings AS (
    SELECT
        pd.buyer_org_id,
        pi.product_id,
        SUM(pi.total_amount) AS total_purchase_amount,
        ROW_NUMBER() OVER (
            PARTITION BY pd.buyer_org_id 
            ORDER BY SUM(pi.total_amount) DESC
        ) AS rank_within_buyer
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    WHERE pi.updated_date BETWEEN p.start_date AND p.end_date
    GROUP BY pd.buyer_org_id, pi.product_id
)

SELECT 
    pr.buyer_org_id,
    pr.product_id,
    vp.product_name,
    pr.total_purchase_amount,
    pr.rank_within_buyer
FROM product_rankings pr
LEFT JOIN vendor_products vp ON pr.product_id = vp.id
WHERE pr.rank_within_buyer <= (SELECT top_n FROM params)
ORDER BY pr.buyer_org_id, pr.rank_within_buyer;

-- @name: top_suppliers
-- @description: Top suppliers by purchase amount

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        %(top_n)s AS top_n
),

supplier_rankings AS (
    SELECT
        pd.buyer_org_id,
        pd.seller_org_id,
        SUM(pi.total_amount) AS total_purchase_amount,
        ROW_NUMBER() OVER (
            PARTITION BY pd.buyer_org_id 
            ORDER BY SUM(pi.total_amount) DESC
        ) AS rank_within_buyer
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    CROSS JOIN params p
    WHERE pi.updated_date BETWEEN p.start_date AND p.end_date
    GROUP BY pd.buyer_org_id, pd.seller_org_id
)

SELECT 
    sr.buyer_org_id,
    sr.seller_org_id,
    so.company_name,
    sr.total_purchase_amount,
    sr.rank_within_buyer
FROM supplier_rankings sr
LEFT JOIN "userApis_organization" so ON sr.seller_org_id = so.org_id
WHERE sr.rank_within_buyer <= (SELECT top_n FROM params)
ORDER BY sr.buyer_org_id, sr.rank_within_buyer;

-- @name: top_categories
-- @description: Top categories by purchase amount

WITH params AS (
    SELECT 
        %(start_date)s::DATE AS start_date,
        %(end_date)s::DATE AS end_date,
        %(top_n)s AS top_n
),

category_rankings AS (
    SELECT
        pd.buyer_org_id,
        (SELECT cat->>'name'
            FROM jsonb_array_elements(vp.category_ids -> 'cat_0') cat
            ORDER BY (cat->>'level')::INT DESC
            LIMIT 1
        ) AS category,
        SUM(pi.total_amount) AS total_purchase_amount,
        ROW_NUMBER() OVER (
            PARTITION BY pd.buyer_org_id 
            ORDER BY SUM(pi.total_amount) DESC
        ) AS rank_within_buyer
    FROM po_items pi
    JOIN po_details pd ON pi.po_id = pd.id
    JOIN vendor_products vp ON pi.product_id = vp.id 
        AND pd.seller_org_id = vp.org_id
    CROSS JOIN params p
    WHERE pi.updated_date BETWEEN p.start_date AND p.end_date
    GROUP BY pd.buyer_org_id, category
)

SELECT 
    cr.buyer_org_id,
    cr.category,
    cr.total_purchase_amount,
    cr.rank_within_buyer
FROM category_rankings cr
WHERE cr.rank_within_buyer <= (SELECT top_n FROM params)
ORDER BY cr.buyer_org_id, cr.rank_within_buyer;