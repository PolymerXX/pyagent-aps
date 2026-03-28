"""订单管理页面

管理生产订单的增删改查
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
import streamlit as st

from ui.utils import init_page
from ui.state import AppState

init_page("订单管理", "📋")

from aps.models.order import Order, Product, ProductType
from ui.utils import generate_order_id, generate_product_id, get_due_color, get_due_emoji

st.title("📋 订单管理")
st.markdown("管理生产订单，支持新增、编辑和删除操作")

orders = AppState.get_orders()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

total_quantity = sum(o.quantity for o in orders)
urgent_count = sum(1 for o in orders if o.due_date <= 24)
avg_priority = sum(o.priority for o in orders) / len(orders) if orders else 0

with col_m1:
    st.metric("订单总数", len(orders))

with col_m2:
    st.metric("总数量", f"{total_quantity:,}")

with col_m3:
    st.metric("紧急订单", urgent_count, delta=f"≤24h截止")

with col_m4:
    st.metric("平均优先级", f"{avg_priority:.1f}")

st.markdown("---")

st.markdown("### 订单列表")

if orders:
    order_table_data = []
    for o in orders:
        due_emoji = get_due_emoji(o.due_date)
        est_hours = o.estimated_production_hours
        order_table_data.append(
            {
                "订单ID": o.id,
                "产品": o.product.name,
                "类型": o.product.product_type.value,
                "数量": f"{o.quantity:,}",
                "截止时间": f"{due_emoji} {o.due_date}h",
                "优先级": f"⭐{o.priority}",
                "预估工时": f"{est_hours:.1f}h",
                "利润/单位": f"¥{o.product.unit_profit:.2f}",
            }
        )

    df_orders = pd.DataFrame(order_table_data)
    st.dataframe(df_orders, use_container_width=True, hide_index=True)
else:
    st.info("暂无订单数据")

st.markdown("---")

col_add, col_del = st.columns([3, 1])

with col_add:
    st.markdown("### ➕ 新增订单")

    with st.form("add_order_form"):
        col_form1, col_form2, col_form3 = st.columns(3)

        with col_form1:
            new_product_name = st.text_input("产品名称", placeholder="例如：可乐 500ml")
            new_product_type = st.selectbox(
                "产品类型",
                options=list(ProductType),
                format_func=lambda x: {
                    ProductType.BEVERAGE: "🥤 饮料",
                    ProductType.JUICE: "🧃 果汁",
                    ProductType.DAIRY: "🥛 乳制品",
                }.get(x, x.value),
            )
            new_production_rate = st.number_input(
                "生产速率 (单位/h)", min_value=100, max_value=10000, value=2000, step=100
            )

        with col_form2:
            new_quantity = st.number_input(
                "订单数量", min_value=100, max_value=100000, value=5000, step=500
            )
            new_due_date = st.number_input(
                "截止时间 (小时)", min_value=1, max_value=720, value=48, step=1
            )
            new_priority = st.slider("优先级", min_value=1, max_value=10, value=5)

        with col_form3:
            new_unit_profit = st.number_input(
                "单位利润 (元)", min_value=0.0, max_value=10.0, value=0.5, step=0.1
            )
            new_min_start = st.number_input("最早开始时间 (h)", min_value=0, max_value=720, value=0)

        submitted = st.form_submit_button("添加订单", type="primary", use_container_width=True)

        if submitted and new_product_name:
            product_id = generate_product_id(orders)
            order_id = generate_order_id(orders)

            new_order = Order(
                id=order_id,
                product=Product(
                    id=product_id,
                    name=new_product_name,
                    product_type=new_product_type,
                    production_rate=new_production_rate,
                    unit_profit=new_unit_profit,
                ),
                quantity=new_quantity,
                due_date=new_due_date,
                priority=new_priority,
                min_start_time=new_min_start,
            )

            AppState.add_order(new_order)
            st.success(f"订单 {order_id} 已添加！")
            st.rerun()

with col_del:
    st.markdown("### 🗑️ 删除订单")

    if orders:
        order_ids = [o.id for o in orders]
        selected_delete = st.selectbox(
            "选择订单",
            options=order_ids,
            format_func=lambda x: (
                f"{x} - {next((o.product.name for o in orders if o.id == x), '')}"
            ),
        )

        if st.button("删除选中订单", type="primary", use_container_width=True):
            if AppState.remove_order(selected_delete):
                st.success(f"订单 {selected_delete} 已删除")
                st.rerun()
            else:
                st.error("删除失败")
    else:
        st.info("暂无可删除的订单")

st.markdown("---")

st.markdown("### ✏️ 编辑订单")

if orders:
    edit_order_id = st.selectbox(
        "选择要编辑的订单",
        options=[o.id for o in orders],
        format_func=lambda x: f"{x} - {next((o.product.name for o in orders if o.id == x), '')}",
        key="edit_order_select",
    )

    target_order = AppState.get_order_by_id(edit_order_id)

    if target_order:
        col_edit1, col_edit2, col_edit3 = st.columns(3)

        with col_edit1:
            edit_quantity = st.number_input(
                "数量",
                value=target_order.quantity,
                min_value=100,
                max_value=100000,
                step=500,
                key="edit_quantity",
            )
            edit_due_date = st.number_input(
                "截止时间 (h)",
                value=target_order.due_date,
                min_value=1,
                max_value=720,
                key="edit_due_date",
            )

        with col_edit2:
            edit_priority = st.slider(
                "优先级",
                min_value=1,
                max_value=10,
                value=target_order.priority,
                key="edit_priority",
            )
            edit_min_start = st.number_input(
                "最早开始时间 (h)",
                value=target_order.min_start_time,
                min_value=0,
                max_value=720,
                key="edit_min_start",
            )

        with col_edit3:
            edit_rate = st.number_input(
                "生产速率",
                value=int(target_order.product.production_rate),
                min_value=100,
                max_value=10000,
                step=100,
                key="edit_rate",
            )
            edit_profit = st.number_input(
                "单位利润",
                value=target_order.product.unit_profit,
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                key="edit_profit",
            )

        if st.button("保存修改", type="primary", use_container_width=True):
            updated = Order(
                id=target_order.id,
                product=Product(
                    id=target_order.product.id,
                    name=target_order.product.name,
                    product_type=target_order.product.product_type,
                    production_rate=edit_rate,
                    unit_profit=edit_profit,
                ),
                quantity=edit_quantity,
                due_date=edit_due_date,
                priority=edit_priority,
                min_start_time=edit_min_start,
            )
            if AppState.update_order(edit_order_id, updated):
                st.success("订单已更新")
                st.rerun()
            else:
                st.error("更新失败")

st.markdown("---")

col_reset, _ = st.columns([1, 3])

with col_reset:
    if st.button("🔄 重置为示例数据", use_container_width=True):
        AppState.reset_all()
        st.success("已重置为示例数据")
        st.rerun()
