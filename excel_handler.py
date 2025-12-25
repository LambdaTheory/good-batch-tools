import pandas as pd
import json
import datetime
import numpy as np

class ExcelHandler:
    def __init__(self, filepath):
        self.filepath = filepath

    def _to_python_type(self, val):
        if pd.isna(val):
            return None
        if hasattr(val, 'item'):
            return val.item()
        return val

    def parse(self):
        """
        Parses the Excel file and returns a list of product dictionaries with nested SKUs.
        """
        try:
            df = pd.read_excel(self.filepath)
            
            # Clean column names: strip whitespace
            df.columns = df.columns.str.strip()
            
            # Debug: Print found columns
            print(f"DEBUG: Found Excel columns: {df.columns.tolist()}")

            # Map Chinese headers to English keys
            # Note: The keys must match what we want to use in logic
            column_map = {
                "类目ID(必填)": "categoryId",
                "商品标题(必填)": "title",
                "商家商品编码(必填,用于分组)": "outItemId",
                "商品详情页地址(必填)": "path",
                "增值服务价格(元)": "service_price",
                "起租天数(默认1)": "rent_from_numbers_of_day",
                "成色等级(默认99新)": "item_fineness_grade",
                "商家SKU编码": "outSkuId",
                "最低日单价(元)": "salePrice",
                "SKU规格名称": "sku_name",
                "SKU租期(天,逗号分隔)": "rent_durations",
                "SKU租期总价(元,格式 天数:价格,逗号分隔)": "sku_prices",
                "每日库存数量": "stock_quantity"
            }
            
            # Rename columns
            df = df.rename(columns=column_map)
            
            # Replace NaN
            df = df.where(pd.notnull(df), None)
            
            # Group by outItemId
            products = []
            if 'outItemId' not in df.columns:
                 print(f"ERROR: Missing 'outItemId' column after mapping. Columns are: {df.columns.tolist()}")
                 return [{"error": "Missing '商家商品编码(必填,用于分组)' column or mapping failed"}]

            grouped = df.groupby('outItemId')
            
            for out_item_id, group in grouped:
                # Master row is the first row of the group
                master = group.iloc[0]
                
                # 1. Basic Product Info
                # Convert potentially numpy types to python types
                product = {
                    "categoryId": str(self._to_python_type(master.get('categoryId', ''))),
                    "title": self._to_python_type(master.get('title', '')),
                    "outItemId": str(self._to_python_type(out_item_id)),
                    "path": self._to_python_type(master.get('path', '')),
                    "rent_from_numbers_of_day": str(self._to_python_type(master.get('rent_from_numbers_of_day') or '1')),
                    "item_fineness_grade": self._to_python_type(master.get('item_fineness_grade') or '99新'),
                    "service_price": self._to_python_type(master.get('service_price')),
                    "skus": []
                }
                
                # 2. Build SKUs
                for _, row in group.iterrows():
                    sku = {}
                    sku['outSkuId'] = str(self._to_python_type(row.get('outSkuId', '')))
                    
                    # salePrice
                    raw_sale_price = row.get('salePrice')
                    try:
                        if raw_sale_price:
                            sku['salePrice'] = int(float(raw_sale_price) * 100)
                        else:
                            sku['salePrice'] = 0
                    except:
                        sku['salePrice'] = 0

                    sku['sku_name'] = self._to_python_type(row.get('sku_name', ''))
                    
                    # Parse Rent Durations and Prices
                    durations = []
                    duration_prices = []
                    
                    raw_durations = str(self._to_python_type(row.get('rent_durations', '')))
                    raw_prices = str(self._to_python_type(row.get('sku_prices', '')))
                    
                    if raw_durations and raw_durations.lower() != 'none':
                        try:
                            durations = [int(float(x.strip())) for x in raw_durations.replace('，', ',').split(',') if x.strip()]
                        except:
                            durations = []
                    
                    if raw_prices and raw_prices.lower() != 'none':
                        # Expecting "1:100, 3:200"
                        pairs = raw_prices.replace('，', ',').split(',')
                        for p in pairs:
                            if ':' in p or '：' in p:
                                try:
                                    d, price = p.replace('：', ':').split(':')
                                    duration_prices.append({
                                        "duration": int(float(d.strip())),
                                        "totalSalePrice": int(float(price.strip()) * 100) # Convert to cents
                                    })
                                except:
                                    pass
                    
                    sku['rent_duration'] = durations
                    sku['durationPriceList'] = duration_prices
                    
                    # Parse Stock
                    stock_qty = self._to_python_type(row.get('stock_quantity'))
                    stock_json = "[]"
                    if stock_qty is not None:
                        try:
                            qty = int(stock_qty)
                            date_list = []
                            today = datetime.date.today()
                            for i in range(90):
                                d = today + datetime.timedelta(days=i)
                                date_str = d.strftime('%Y%m%d')
                                date_list.append({"date": date_str, "quantity": qty})
                            stock_json = json.dumps(date_list)
                        except:
                            pass
                    sku['stock_json'] = stock_json
                    
                    product['skus'].append(sku)
                
                products.append(product)
                
            return products
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return [{"error": str(e)}]
