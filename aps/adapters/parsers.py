"""统一数据解析和类型映射"""

from aps.models.order import ProductType

PRODUCT_TYPE_MAP: dict[str, ProductType] = {
    "cola": ProductType.BEVERAGE,
    "beverage": ProductType.BEVERAGE,
    "drink": ProductType.BEVERAGE,
    "soda": ProductType.BEVERAGE,
    "饮料": ProductType.BEVERAGE,
    "碳酸饮料": ProductType.BEVERAGE,
    "milk": ProductType.DAIRY,
    "dairy": ProductType.DAIRY,
    "yogurt": ProductType.DAIRY,
    "乳制品": ProductType.DAIRY,
    "牛奶": ProductType.DAIRY,
    "奶制品": ProductType.DAIRY,
    "juice": ProductType.JUICE,
    "orange_juice": ProductType.JUICE,
    "apple_juice": ProductType.JUICE,
    "果汁": ProductType.JUICE,
    "橙汁": ProductType.JUICE,
}

DEFAULT_PRODUCTION_RATE: float = 100.0


def parse_product_type(raw: str | None) -> ProductType:
    if raw is None:
        raise ValueError("product_type is required but got None")

    key = str(raw).lower().strip()
    if not key:
        raise ValueError("product_type is required but got empty string")

    if key in PRODUCT_TYPE_MAP:
        return PRODUCT_TYPE_MAP[key]

    for member in ProductType:
        if member.value == key:
            return member

    raise ValueError(
        f"Unknown product_type: '{raw}'. Supported values: {list(set(PRODUCT_TYPE_MAP.keys()))}"
    )


def parse_product_type_with_default(
    raw: str | None, default: ProductType = ProductType.BEVERAGE
) -> ProductType:
    try:
        return parse_product_type(raw)
    except ValueError:
        return default
