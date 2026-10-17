import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم العريض المتجاوب مع الموبايل
# ---------------------------------------------------------
st.set_page_config(
    page_title="مستشفى الشوملي العام | المذخر الصيدلاني السحابي",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. إعدادات الاتصال بالسحابة (Supabase)
# ---------------------------------------------------------
SUPABASE_URL = "https://dhpkarxgraruspswdvsq.supabase.co"
SUPABASE_KEY = "sb_publishable_4YzTmeXOqgcLyK7UaPbDJw_qwEHNjSI"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"❌ تعذر الاتصال بالسحابة: {e}")
    st.stop()

# قائمة البوابات الفرعية
SUB_PORTALS_LIST = [
    "البرنامج الرئيسي (MAIN_ADMIN)",
    "الصيدلية الداخلية", "الصيدلية الاستشاريه", "صيدلية الطوارئ",
    "الصيدلية الخارجية الخافرة", "الداخلية الخافرة", "الجناح العام الرجالي",
    "الجناح العام النسائي", "جناح الاطفال", "الخدج", "صالة الولادة",
    "صاله العمليات / الجناح الخاص", "الاسنان", "الاشعة", "السونار",
    "الطوارئ العامه", "الاسعاف الفوري", "الخدمات", "المختبرات",
    "الوبائيه", "لوكرات الصدمة", "الجناح الخاص", "العمليات"
]

DEFAULT_REGISTERS = [
    "الحياتية", "الامبولات والفيالات", "المساحيق والشرابات",
    "الحبوب والكباسيل", "المؤثرات العقلية", "المخدرات",
    "مستلزمات القسم", "اللقاحات", "مشتريات الادويه",
    "مشتريات المستلزمات", "مشتريات الجناح الخاص"
]

# ---------------------------------------------------------
# 3. القائمة الجانبية (اختيار البوابة والسجل)
# ---------------------------------------------------------
st.sidebar.title("🏥 مستشفى الشوملي العام")
st.sidebar.markdown("**نظام إدارة المذخر والصيدلية الذكي**")

selected_portal = st.sidebar.selectbox("🔑 اختر البوابة / القسم:", SUB_PORTALS_LIST)
portal_scope = "MAIN_ADMIN" if selected_portal == "البرنامج الرئيسي (MAIN_ADMIN)" else selected_portal

# جلب السجلات المخصصة للبوابة من السحابة
@st.cache_data(ttl=5)
def get_cloud_registers(scope):
    try:
        res = supabase.table("custom_registers").select("register_name").eq("portal_scope", scope).execute()
        if res.data:
            return [r["register_name"] for r in res.data]
    except Exception:
        pass
    return DEFAULT_REGISTERS

registers_list = get_cloud_registers(portal_scope)
selected_register = st.sidebar.selectbox("📋 اختر السجل:", registers_list)

# زر إضافة سجل جديد سحابياً
with st.sidebar.expander("➕ إضافة سجل جديد"):
    new_reg_name = st.text_input("اسم السجل الجديد:")
    if st.button("حفظ السجل بالسحابة"):
        if new_reg_name.strip():
            supabase.table("custom_registers").insert({
                "portal_scope": portal_scope,
                "register_name": new_reg_name.strip()
            }).execute()
            st.success("تمت إضافة السجل بنجاح!")
            st.rerun()

st.sidebar.divider()
st.sidebar.button("🔄 تحديث البيانات اللحظي", on_click=lambda: st.cache_data.clear())

# ---------------------------------------------------------
# 4. جلب وعرض البيانات من السحابة مباشرة
# ---------------------------------------------------------
@st.cache_data(ttl=2)
def fetch_items(scope, reg):
    try:
        res = supabase.table("items").select("*").eq("portal_scope", scope).eq("register_name", reg).execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"خطأ في جلب البيانات: {e}")
        return []

items_data = fetch_items(portal_scope, selected_register)

# ---------------------------------------------------------
# 5. الواجهة الرئيسية وبطاقات الإحصائيات
# ---------------------------------------------------------
st.title(f"📊 المذخر الصيدلاني | {selected_portal}")
st.caption(f"السجل الحالي: **{selected_register}** (مزامنة سحابية لحظية 100%)")

col1, col2, col3, col4 = st.columns(4)

total_items = len(items_data)
low_stock = sum(1 for i in items_data if (i.get("remaining_qty") or 0) < 10)
total_value = sum((i.get("remaining_qty") or 0) * (i.get("unit_price_iqd") or 0) for i in items_data)

col1.metric("عدد المواد بالسجل", total_items)
col2.metric("مخزون منخفض / حرج", low_stock, delta_color="inverse")
col3.metric("القيمة الإجمالية", f"{total_value:,.0f} IQD")
col4.metric("حالة الاتصال", "🟢 سحابي متصل")

st.divider()

# ---------------------------------------------------------
# 6. إجراءات العمليات (إضافة مادة / تخريج يومي / توريد)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📦 عرض الجدول والمخزون", "➕ إضافة مادة جديدة", "⬇ تخريج يومي (صرف)", "📥 توريد وجبة شهرية"])

with tab1:
    search_q = st.text_input("🔍 بحث عن مادة (بالاسم أو الرمز الوطني):")
    if items_data:
        df = pd.DataFrame(items_data)
        
        # اختيار وتنسيق الأعمدة المعروضة
        show_cols = ["id", "national_code", "item_name", "item_name_en", "remaining_qty", "dispensed_qty", "total_qty", "unit_price_iqd", "expiry_date", "batch_number"]
        available_cols = [c for c in show_cols if c in df.columns]
        df_display = df[available_cols]

        if search_q:
            df_display = df_display[df_display["item_name"].astype(str).str.contains(search_q, case=False, na=False) | 
                                    df_display["national_code"].astype(str).str.contains(search_q, case=False, na=False)]

        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "id": "ID",
                "national_code": "الرمز الوطني",
                "item_name": "اسم المادة (عربي)",
                "item_name_en": "اسم المادة (إنجليزي)",
                "remaining_qty": "المتبقي",
                "dispensed_qty": "المصروف",
                "total_qty": "الوارد الكلي",
                "unit_price_iqd": "السعر (IQD)",
                "expiry_date": "تاريخ الانتهاء",
                "batch_number": " الوجبة Batch"
            }
        )
    else:
        st.info("لا توجد مواد مسجلة في هذا السجل حالياً.")

with tab2:
    st.subheader("إضافة مادة جديدة إلى السجل السحابي")
    with st.form("add_item_form"):
        f_name = st.text_input("اسم المادة باللغة العربية *")
        f_name_en = st.text_input("اسم المادة باللغة الإنجليزية")
        f_code = st.text_input("الرمز الوطني (National Code)")
        f_qty = st.number_input("الكمية الواردة التأسيسية", min_value=1, value=100)
        f_price = st.number_input("سعر الوحدة (IQD)", min_value=0.0, value=0.0)
        f_batch = st.text_input("رقم الوجبة Batch No")
        f_exp = st.date_input("تاريخ الانتهاء")

        submit_btn = st.form_submit_button("💾 حفظ المادة ومزامنتها فوراً")
        if submit_btn:
            if f_name.strip():
                supabase.table("items").insert({
                    "portal_scope": portal_scope,
                    "register_name": selected_register,
                    "item_name": f_name.strip(),
                    "item_name_en": f_name_en.strip(),
                    "national_code": f_code.strip(),
                    "total_qty": f_qty,
                    "remaining_qty": f_qty,
                    "dispensed_qty": 0,
                    "unit_price_iqd": f_price,
                    "batch_number": f_batch.strip(),
                    "expiry_date": str(f_exp),
                    "date_added": datetime.now().strftime("%Y-%m-%d")
                }).execute()
                st.success(f"تمت إضافة ({f_name}) ومزامنتها مع جميع الأجهزة بنجاح!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("يرجى إدخال اسم المادة بالعربي.")

with tab3:
    st.subheader("تخريج يومي للمنافذ والأقسام (FIFO)")
    if items_data:
        item_options = {f"{i['item_name']} (المتبقي: {i.get('remaining_qty', 0)})": i for i in items_data}
        selected_item_str = st.selectbox("اختر المادة للتخريج:", list(item_options.keys()))
        target_item = item_options[selected_item_str]

        with st.form("dispense_form"):
            disp_qty = st.number_input("الكمية المصروفة:", min_value=1, max_value=max(1, target_item.get("remaining_qty", 1)))
            destination = st.selectbox("جهة الصرف / المنفذ:", SUB_PORTALS_LIST[1:])
            letter_ref = st.text_input("رقم كتاب الطلبية / الإذن:")
            
            disp_btn = st.form_submit_button("تأكيد التخريج والخصم اللحظي")
            if disp_btn:
                curr_rem = target_item.get("remaining_qty", 0)
                curr_disp = target_item.get("dispensed_qty", 0)
                new_rem = max(0, curr_rem - disp_qty)
                new_disp = curr_disp + disp_qty

                # 1. تحديث جدول المادة بالسحابة
                supabase.table("items").update({
                    "remaining_qty": new_rem,
                    "dispensed_qty": new_disp,
                    "dispense_location": destination
                }).eq("id", target_item["id"]).execute()

                # 2. تسجيل الحركة في سجل التخريج السحابي
                supabase.table("daily_dispense_log").insert({
                    "item_id": target_item["id"],
                    "dispensed_amount": disp_qty,
                    "destination": destination,
                    "letter_ref": letter_ref,
                    "remaining_after_dispense": new_rem,
                    "dispense_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }).execute()

                st.success(f"تم خصم {disp_qty} قطعة وتحديث الرصيد اللحظي لدى جميع الأجهزة إلى ({new_rem}).")
                st.cache_data.clear()
                st.rerun()

with tab4:
    st.subheader("إضافة توريد وجبة شهرية جديدة")
    if items_data:
        item_options_inbound = {f"{i['item_name']}": i for i in items_data}
        selected_inbound_str = st.selectbox("اختر المادة لتوريد الوجبة:", list(item_options_inbound.keys()), key="inbound_sel")
        target_inbound = item_options_inbound[selected_inbound_str]

        with st.form("inbound_form"):
            inbound_qty = st.number_input("الكمية الواردة الجديدة:", min_value=1, value=100)
            inbound_letter = st.text_input("رقم كتاب التجهيز:")
            inbound_batch = st.text_input("رقم الوجبة الجديد Batch No:")
            inbound_exp = st.date_input("تاريخ الانتهاء للوجبة:")

            inbound_btn = st.form_submit_button("تسجيل التوريد وتحديث الرصيد")
            if inbound_btn:
                curr_tot = target_inbound.get("total_qty", 0)
                curr_rem = target_inbound.get("remaining_qty", 0)
                
                supabase.table("items").update({
                    "total_qty": curr_tot + inbound_qty,
                    "remaining_qty": curr_rem + inbound_qty,
                    "incoming_letter_no": inbound_letter,
                    "batch_number": inbound_batch,
                    "expiry_date": str(inbound_exp)
                }).eq("id", target_inbound["id"]).execute()

                st.success("تم تسجيل الوجبة وتحديث الرصيد السحابي بنجاح!")
                st.cache_data.clear()
                st.rerun()