"""The wizard question tree.

This file is the single source of truth for what the bot asks. Changing the intake
means editing this file only — the engine, keyboards, renderer and storage are all
driven by these declarations.

Copy rules (from CONTEXT.md):
  • Persian written natively, never translated. ZWNJ half-spaces applied.
  • Questions are phrased as business outcomes, not technical specifications.
  • Every step reduces uncertainty: the user always knows why we ask and what is next.
  • No pressure, no pricing promises, no jargon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

Answers = dict[str, object]

# --------------------------------------------------------------------------
# Delivery promise for poster / banner / cover / thumbnail work:
# one working day per batch of three designs. This is a CEILING we commit to,
# not an average — a promise kept is the product (see CONTEXT.md §2).
# --------------------------------------------------------------------------
DESIGNS_PER_WORKING_DAY = 3


def design_delivery_days(design_count: int) -> int:
    """3 designs -> 1 day, 6 -> 2 days, 7 -> 3 days."""
    return max(1, math.ceil(design_count / DESIGNS_PER_WORKING_DAY))


@dataclass(frozen=True)
class Option:
    key: str
    label: str


@dataclass(frozen=True)
class Step:
    id: str
    kind: str  # "choice" | "multi" | "text"
    title: str
    help: str = ""
    options: tuple[Option, ...] = ()
    validator: str = "free_text"
    placeholder: str = ""
    optional: bool = False
    min_select: int = 1
    columns: int = 1
    summary_label: str = ""
    show_if: Callable[[Answers], bool] | None = None
    section: str = ""

    def label(self) -> str:
        return self.summary_label or self.title

    def visible(self, answers: Answers) -> bool:
        return True if self.show_if is None else bool(self.show_if(answers))

    def option_label(self, key: str) -> str:
        for opt in self.options:
            if opt.key == key:
                return opt.label
        return key


def service_is(*services: str) -> Callable[[Answers], bool]:
    return lambda a: a.get("service") in services


# --------------------------------------------------------------------------
# Budget tiers — REVIEW THESE EVERY QUARTER.
# Iranian inflation ages fixed ranges fast; stale numbers make us look out of
# touch, which is the opposite of the trust this bot is meant to build.
# Values are in Toman.
# --------------------------------------------------------------------------
BUDGET_OPTIONS = (
    Option("b1", "تا ۱۵ میلیون تومان"),
    Option("b2", "۱۵ تا ۴۰ میلیون تومان"),
    Option("b3", "۴۰ تا ۱۰۰ میلیون تومان"),
    Option("b4", "بیش از ۱۰۰ میلیون تومان"),
    Option("b0", "ترجیح می‌دهم در گفت‌وگو مشخص شود"),
)

# Poster / banner / cover / thumbnail work is an order of magnitude cheaper than a
# build project. Showing build-sized ranges to someone ordering one thumbnail reads
# as "you are not our customer" and loses the lead.
DESIGN_BUDGET_OPTIONS = (
    Option("d1", "۳۰۰ هزار تا ۱ میلیون تومان"),
    Option("d2", "۱ تا ۳ میلیون تومان"),
    Option("d3", "۳ تا ۶ میلیون تومان"),
    Option("d4", "۶ تا ۱۰ میلیون تومان"),
    Option("d0", "ترجیح می‌دهم در گفت‌وگو مشخص شود"),
)


SERVICE_OPTIONS = (
    Option("website", "طراحی و توسعهٔ وب‌سایت"),
    Option("automation", "اتوماسیون و یکپارچه‌سازی فرایندها"),
    Option("bot", "ربات پیام‌رسان"),
    Option("inventory", "سیستم انبارداری و مدیریت موجودی"),
    Option("graphic", "طراحی پوستر، بنر، کاور و تامبنیل"),
    Option("consulting", "هنوز مطمئن نیستم؛ به مشاوره نیاز دارم"),
)


FLOW: tuple[Step, ...] = (
    # ---------------------------------------------------------------- entry
    Step(
        id="service",
        kind="choice",
        section="شروع",
        title="برای کدام حوزه به ما نیاز دارید؟",
        help="اگر بین دو گزینه مردد هستید، گزینهٔ آخر را انتخاب کنید؛ در گفت‌وگو با هم روشنش می‌کنیم.",
        options=SERVICE_OPTIONS,
        summary_label="نوع خدمت",
    ),
    # ------------------------------------------------------------- website
    Step(
        id="w_type",
        kind="choice",
        section="وب‌سایت",
        title="چه نوع وب‌سایتی مدنظرتان است؟",
        options=(
            Option("corporate", "سایت شرکتی و معرفی خدمات"),
            Option("shop", "فروشگاه اینترنتی"),
            Option("webapp", "وب‌اپلیکیشن یا پنل کاربری"),
            Option("media", "سایت محتوایی، خبری یا وبلاگ"),
            Option("landing", "لندینگ‌پیج برای یک کمپین مشخص"),
            Option("other", "موردی غیر از این‌ها"),
        ),
        summary_label="نوع وب‌سایت",
        show_if=service_is("website"),
    ),
    Step(
        id="w_status",
        kind="choice",
        section="وب‌سایت",
        title="در حال حاضر وب‌سایت دارید؟",
        options=(
            Option("none", "خیر، از صفر شروع می‌کنیم"),
            Option("redesign", "بله، اما نیاز به بازطراحی کامل دارد"),
            Option("extend", "بله، فقط توسعه یا رفع مشکل می‌خواهم"),
            Option("migrate", "بله، اما می‌خواهم به بستر دیگری منتقل شود"),
        ),
        summary_label="وضعیت فعلی",
        show_if=service_is("website"),
    ),
    Step(
        id="w_url",
        kind="text",
        section="وب‌سایت",
        title="آدرس وب‌سایت فعلی‌تان را بنویسید.",
        help="پیش از هر پیشنهادی، وضعیت فعلی را بررسی می‌کنیم.",
        validator="url",
        placeholder="مثال: bizynex.com",
        summary_label="آدرس سایت فعلی",
        show_if=lambda a: a.get("service") == "website"
        and a.get("w_status") in {"redesign", "extend", "migrate"},
    ),
    Step(
        id="w_scale",
        kind="choice",
        section="وب‌سایت",
        title="تقریباً چند صفحه یا بخش اصلی خواهید داشت؟",
        help="اگر دقیق نمی‌دانید اشکالی ندارد؛ فقط برای برآورد اولیهٔ حجم کار است.",
        options=(
            Option("s1", "تک‌صفحه‌ای"),
            Option("s2", "۲ تا ۵ صفحه"),
            Option("s3", "۶ تا ۱۵ صفحه"),
            Option("s4", "بیش از ۱۵ صفحه"),
            Option("s0", "هنوز مشخص نیست"),
        ),
        summary_label="حجم تقریبی",
        show_if=service_is("website"),
    ),
    Step(
        id="w_features",
        kind="multi",
        section="وب‌سایت",
        title="کدام قابلیت‌ها برایتان اهمیت دارد؟",
        help="هر تعداد که لازم است انتخاب کنید، سپس «تأیید و ادامه» را بزنید.",
        options=(
            Option("payment", "پرداخت آنلاین"),
            Option("seo", "بهینه‌سازی برای موتورهای جست‌وجو"),
            Option("multilang", "چندزبانه بودن"),
            Option("panel", "پنل مدیریت اختصاصی"),
            Option("booking", "رزرو یا نوبت‌دهی"),
            Option("integration", "اتصال به سامانه‌های فعلی کسب‌وکار"),
            Option("blog", "بخش مقالات و محتوا"),
            Option("none", "فعلاً هیچ‌کدام"),
        ),
        summary_label="قابلیت‌های موردنیاز",
        show_if=service_is("website"),
    ),
    Step(
        id="w_content",
        kind="choice",
        section="وب‌سایت",
        title="محتوا و تصاویر سایت آماده است؟",
        help="این پرسش روی زمان‌بندی پروژه اثر مستقیم دارد؛ شفاف بودنش از تأخیرهای بعدی جلوگیری می‌کند.",
        options=(
            Option("ready", "بله، کامل آماده است"),
            Option("partial", "بخشی آماده است"),
            Option("none", "خیر، به تولید محتوا نیاز داریم"),
        ),
        summary_label="وضعیت محتوا",
        show_if=service_is("website"),
    ),
    Step(
        id="w_goal",
        kind="text",
        section="وب‌سایت",
        title="مهم‌ترین نتیجه‌ای که از این سایت انتظار دارید چیست؟",
        help="مثلاً «تماس بیشتر از مشتریان صنعتی» یا «فروش مستقیم بدون واسطه». هرچه دقیق‌تر، پیشنهاد ما دقیق‌تر.",
        placeholder="در یک یا دو جمله بنویسید",
        summary_label="نتیجهٔ موردانتظار",
        show_if=service_is("website"),
    ),
    # ---------------------------------------------------------- automation
    Step(
        id="a_areas",
        kind="multi",
        section="اتوماسیون",
        title="کدام بخش‌های کارتان بیشترین کار دستی را دارد؟",
        options=(
            Option("sales", "فروش و پیگیری مشتری"),
            Option("finance", "مالی، فاکتور و پرداخت‌ها"),
            Option("inventory", "انبار و ثبت سفارش"),
            Option("support", "پشتیبانی و پاسخ به مشتری"),
            Option("hr", "منابع انسانی و حضور و غیاب"),
            Option("report", "گزارش‌گیری و تحلیل"),
            Option("other", "بخشی غیر از این‌ها"),
        ),
        summary_label="حوزه‌های اتوماسیون",
        show_if=service_is("automation"),
    ),
    Step(
        id="a_current",
        kind="choice",
        section="اتوماسیون",
        title="این کارها الان چطور انجام می‌شود؟",
        options=(
            Option("paper", "دستی و کاغذی"),
            Option("excel", "با اکسل یا گوگل‌شیت"),
            Option("split", "چند نرم‌افزار جدا که به هم وصل نیستند"),
            Option("legacy", "یک نرم‌افزار قدیمی که پاسخگو نیست"),
        ),
        summary_label="وضعیت فعلی فرایند",
        show_if=service_is("automation"),
    ),
    Step(
        id="a_tools",
        kind="text",
        section="اتوماسیون",
        title="از چه ابزارها یا نرم‌افزارهایی استفاده می‌کنید؟",
        help="اگر ابزار خاصی ندارید، بنویسید «ندارم».",
        validator="short_text",
        placeholder="مثال: هلو، اکسل، واتساپ",
        summary_label="ابزارهای فعلی",
        show_if=service_is("automation"),
    ),
    Step(
        id="a_users",
        kind="choice",
        section="اتوماسیون",
        title="چند نفر از این سامانه استفاده خواهند کرد؟",
        options=(
            Option("u1", "۱ تا ۳ نفر"),
            Option("u2", "۴ تا ۱۰ نفر"),
            Option("u3", "۱۱ تا ۳۰ نفر"),
            Option("u4", "بیش از ۳۰ نفر"),
        ),
        summary_label="تعداد کاربران",
        show_if=service_is("automation"),
    ),
    Step(
        id="a_pain",
        kind="text",
        section="اتوماسیون",
        title="پرهزینه‌ترین کار تکراری‌تان کدام است؟",
        help="همان کاری که هر هفته وقت زیادی می‌گیرد و همیشه آرزو می‌کنید خودکار بود.",
        placeholder="در یک یا دو جمله بنویسید",
        summary_label="پرهزینه‌ترین کار تکراری",
        show_if=service_is("automation"),
    ),
    # ----------------------------------------------------------------- bot
    Step(
        id="b_platforms",
        kind="multi",
        section="ربات",
        title="ربات روی کدام پیام‌رسان‌ها کار کند؟",
        options=(
            Option("telegram", "تلگرام"),
            Option("whatsapp", "واتساپ"),
            Option("instagram", "دایرکت اینستاگرام"),
            Option("bale", "بله، ایتا یا سروش"),
            Option("web", "چت روی وب‌سایت"),
        ),
        summary_label="بسترها",
        show_if=service_is("bot"),
    ),
    Step(
        id="b_purpose",
        kind="multi",
        section="ربات",
        title="ربات قرار است چه کاری را برایتان انجام دهد؟",
        options=(
            Option("support", "پاسخ خودکار به پرسش‌های پرتکرار"),
            Option("lead", "جذب و ثبت سرنخ فروش"),
            Option("order", "ثبت سفارش و فروش"),
            Option("notify", "اطلاع‌رسانی به مشتریان"),
            Option("internal", "کارهای داخلی تیم"),
            Option("auth", "عضویت و احراز هویت کاربران"),
        ),
        summary_label="کارکرد ربات",
        show_if=service_is("bot"),
    ),
    Step(
        id="b_payment",
        kind="choice",
        section="ربات",
        title="پرداخت درون ربات لازم دارید؟",
        options=(
            Option("yes", "بله"),
            Option("no", "خیر"),
            Option("unknown", "مطمئن نیستم"),
        ),
        summary_label="پرداخت درون ربات",
        show_if=service_is("bot"),
    ),
    Step(
        id="b_admin",
        kind="choice",
        section="ربات",
        title="به پنل مدیریت برای دیدن داده‌ها نیاز دارید؟",
        help="پنل یعنی بتوانید بدون ما گزارش بگیرید و محتوای ربات را تغییر دهید.",
        options=(
            Option("yes", "بله، حتماً"),
            Option("no", "خیر، فعلاً لازم نیست"),
            Option("unknown", "مطمئن نیستم"),
        ),
        summary_label="پنل مدیریت",
        show_if=service_is("bot"),
    ),
    Step(
        id="b_goal",
        kind="text",
        section="ربات",
        title="موفقیت این ربات را با چه چیزی می‌سنجید؟",
        help="مثلاً «کاهش پیام‌های تکراری پشتیبانی» یا «ثبت سفارش بدون تماس تلفنی».",
        placeholder="در یک یا دو جمله بنویسید",
        summary_label="معیار موفقیت",
        show_if=service_is("bot"),
    ),
    # ----------------------------------------------------------- inventory
    Step(
        id="i_scale",
        kind="choice",
        section="انبارداری",
        title="تقریباً چند قلم کالا دارید؟",
        options=(
            Option("n1", "کمتر از ۱۰۰ قلم"),
            Option("n2", "۱۰۰ تا ۱٬۰۰۰ قلم"),
            Option("n3", "۱٬۰۰۰ تا ۱۰٬۰۰۰ قلم"),
            Option("n4", "بیش از ۱۰٬۰۰۰ قلم"),
        ),
        summary_label="تعداد اقلام",
        show_if=service_is("inventory"),
    ),
    Step(
        id="i_locations",
        kind="choice",
        section="انبارداری",
        title="در چند انبار یا شعبه کار می‌کنید؟",
        options=(
            Option("l1", "یک انبار"),
            Option("l2", "۲ تا ۳ انبار"),
            Option("l3", "بیش از ۳ انبار"),
        ),
        summary_label="تعداد انبار",
        show_if=service_is("inventory"),
    ),
    Step(
        id="i_features",
        kind="multi",
        section="انبارداری",
        title="کدام قابلیت‌ها برایتان ضروری است؟",
        options=(
            Option("barcode", "بارکد یا کیوآر"),
            Option("serial", "سریال و تاریخ انقضا"),
            Option("invoice", "صدور فاکتور و ثبت فروش"),
            Option("report", "گزارش و داشبورد مدیریتی"),
            Option("roles", "چند کاربره با سطح دسترسی"),
            Option("shop", "اتصال به فروشگاه اینترنتی"),
            Option("accounting", "اتصال به نرم‌افزار حسابداری"),
        ),
        summary_label="قابلیت‌های ضروری",
        show_if=service_is("inventory"),
    ),
    Step(
        id="i_current",
        kind="choice",
        section="انبارداری",
        title="موجودی را الان چطور کنترل می‌کنید؟",
        options=(
            Option("paper", "دفتر و کاغذ"),
            Option("excel", "اکسل"),
            Option("legacy", "نرم‌افزاری که جوابگو نیست"),
            Option("none", "روش مشخصی نداریم"),
        ),
        summary_label="روش فعلی کنترل موجودی",
        show_if=service_is("inventory"),
    ),
    Step(
        id="i_pain",
        kind="text",
        section="انبارداری",
        title="بزرگ‌ترین مشکلی که الان با آن روبه‌رو هستید چیست؟",
        help="مثلاً مغایرت موجودی، کندی انبارگردانی، یا نبود گزارش دقیق.",
        placeholder="در یک یا دو جمله بنویسید",
        summary_label="مشکل اصلی",
        show_if=service_is("inventory"),
    ),
    # ------------------------------------------------------- visual artwork
    Step(
        id="g_items",
        kind="multi",
        section="طراحی بصری",
        title="به کدام طرح‌ها نیاز دارید؟",
        help="هر تعداد که لازم است انتخاب کنید، سپس «تأیید و ادامه» را بزنید.",
        options=(
            Option("poster", "پوستر تبلیغاتی"),
            Option("banner", "بنر تبلیغاتی (چاپی یا دیجیتال)"),
            Option("cover", "کاور اینستاگرام"),
            Option("thumbnail", "تامبنیل یوتیوب"),
        ),
        summary_label="نوع طرح",
        show_if=service_is("graphic"),
    ),
    Step(
        id="g_count",
        kind="choice",
        section="طراحی بصری",
        title="تقریباً چند طرح مدنظرتان است؟",
        help="زمان تحویل به ازای هر ۳ طرح یک روز کاری است. عددی که می‌بینید سقف زمان است، نه میانگین.",
        options=(
            Option("c1", "۱ تا ۳ طرح — تحویل تا ۱ روز کاری"),
            Option("c2", "۴ تا ۶ طرح — تحویل تا ۲ روز کاری"),
            Option("c3", "۷ تا ۹ طرح — تحویل تا ۳ روز کاری"),
            Option("c4", "۱۰ تا ۱۵ طرح — تحویل تا ۵ روز کاری"),
            Option("c5", "بیش از ۱۵ طرح — زمان تحویل در گفت‌وگو مشخص می‌شود"),
        ),
        summary_label="تعداد طرح و زمان تحویل",
        show_if=service_is("graphic"),
    ),
    Step(
        id="g_volume",
        kind="choice",
        section="طراحی بصری",
        title="این همکاری یک‌باره است یا مستمر؟",
        help="همکاری مستمر معمولاً هم ارزان‌تر تمام می‌شود و هم ظاهر کارها یکدست می‌ماند.",
        options=(
            Option("once", "یک سفارش مشخص"),
            Option("monthly", "به‌صورت ماهانه و مستمر"),
            Option("seasonal", "فصلی یا کمپین‌محور"),
        ),
        summary_label="نوع همکاری",
        show_if=service_is("graphic"),
    ),
    Step(
        id="g_assets",
        kind="choice",
        section="طراحی بصری",
        title="متن، عکس و لوگوی موردنیاز طرح آماده است؟",
        help="این پرسش روی زمان تحویل اثر مستقیم دارد.",
        options=(
            Option("ready", "بله، همه چیز آماده است"),
            Option("partial", "بخشی آماده است"),
            Option("none", "خیر، باید از ابتدا تهیه شود"),
        ),
        summary_label="وضعیت محتوای طرح",
        show_if=service_is("graphic"),
    ),
    Step(
        id="g_style",
        kind="text",
        section="طراحی بصری",
        title="دو یا سه نمونه که ظاهرشان را می‌پسندید نام ببرید.",
        help="کمک می‌کند سلیقهٔ بصری‌تان را دقیق بفهمیم و آزمون‌وخطا کمتر شود.",
        validator="short_text",
        placeholder="نام برند، پیج اینستاگرام یا کانال یوتیوب",
        summary_label="ارجاع‌های سلیقه‌ای",
        show_if=service_is("graphic"),
    ),
    # ---------------------------------------------------------- consulting
    Step(
        id="c_stage",
        kind="choice",
        section="مشاوره",
        title="کسب‌وکارتان در چه مرحله‌ای است؟",
        options=(
            Option("idea", "در حد ایده"),
            Option("early", "تازه شروع شده"),
            Option("growing", "در حال رشد"),
            Option("established", "جاافتاده و پابرجا"),
        ),
        summary_label="مرحلهٔ کسب‌وکار",
        show_if=service_is("consulting"),
    ),
    Step(
        id="c_problem",
        kind="text",
        section="مشاوره",
        title="مسئله‌ای که می‌خواهید حل شود چیست؟",
        help="لازم نیست راه‌حل فنی بدانید؛ فقط مشکل را همان‌طور که هست بنویسید.",
        placeholder="در چند جمله توضیح دهید",
        summary_label="مسئلهٔ اصلی",
        show_if=service_is("consulting"),
    ),
    Step(
        id="c_tried",
        kind="text",
        section="مشاوره",
        title="تا امروز چه راه‌هایی را امتحان کرده‌اید؟",
        help="اگر هنوز کاری نکرده‌اید، بنویسید «هنوز اقدامی نکرده‌ام».",
        placeholder="در یک یا دو جمله بنویسید",
        summary_label="اقدامات قبلی",
        show_if=service_is("consulting"),
    ),
    # -------------------------------------------------- common tail: timing
    Step(
        id="t_start",
        kind="choice",
        section="زمان و بودجه",
        title="چه زمانی می‌خواهید کار شروع شود؟",
        options=(
            Option("asap", "هرچه زودتر"),
            Option("month", "تا یک ماه آینده"),
            Option("quarter", "یک تا سه ماه آینده"),
            Option("research", "فعلاً در حال بررسی هستم"),
        ),
        summary_label="زمان شروع",
    ),
    Step(
        id="t_budget",
        kind="choice",
        section="زمان و بودجه",
        title="بودجهٔ تقریبی‌تان در چه بازه‌ای است؟",
        help="این پرسش برای قیمت‌گذاری نیست؛ برای این است که پیشنهادی متناسب با شرایط واقعی‌تان بدهیم، نه پیشنهادی که به نتیجه نمی‌رسد.",
        options=BUDGET_OPTIONS,
        summary_label="بازهٔ بودجه",
        show_if=lambda a: a.get("service") != "graphic",
    ),
    Step(
        id="t_budget_design",
        kind="choice",
        section="زمان و بودجه",
        title="بودجهٔ تقریبی‌تان در چه بازه‌ای است؟",
        help="بسته به تعداد طرح‌ها و میزان بازنگری متفاوت است. انتخاب شما فقط برای ارائهٔ پیشنهاد متناسب است.",
        options=DESIGN_BUDGET_OPTIONS,
        summary_label="بازهٔ بودجه",
        show_if=service_is("graphic"),
    ),
    # ------------------------------------------------- common tail: contact
    Step(
        id="t_business",
        kind="text",
        section="اطلاعات تماس",
        title="نام کسب‌وکار و حوزهٔ فعالیتتان را بنویسید.",
        validator="short_text",
        placeholder="مثال: صنایع غذایی آرین — تولید و پخش",
        summary_label="کسب‌وکار",
    ),
    Step(
        id="t_name",
        kind="text",
        section="اطلاعات تماس",
        title="نام و نام خانوادگی شما؟",
        validator="name",
        placeholder="نام و نام خانوادگی خود را کامل بنویسید",
        summary_label="نام",
    ),
    Step(
        id="t_phone",
        kind="text",
        section="اطلاعات تماس",
        title="شمارهٔ تماس شما؟",
        help="فقط برای همین درخواست استفاده می‌شود. نه در جایی منتشر می‌شود و نه به کسی داده می‌شود.",
        validator="phone",
        placeholder="مثال: ۰۹۱۲۱۲۳۴۵۶۷",
        summary_label="شمارهٔ تماس",
    ),
    Step(
        id="t_channel",
        kind="choice",
        section="اطلاعات تماس",
        title="ترجیح می‌دهید از چه راهی با شما تماس بگیریم؟",
        options=(
            Option("telegram", "همین‌جا در تلگرام"),
            Option("call", "تماس تلفنی"),
            Option("whatsapp", "واتساپ"),
            Option("email", "ایمیل"),
        ),
        summary_label="راه ارتباطی",
    ),
    Step(
        id="t_email",
        kind="text",
        section="اطلاعات تماس",
        title="ایمیلتان را بنویسید.",
        validator="email",
        placeholder="مثال: name@example.com",
        summary_label="ایمیل",
        show_if=lambda a: a.get("t_channel") == "email",
    ),
    Step(
        id="t_time",
        kind="choice",
        section="اطلاعات تماس",
        title="بهترین ساعت برای تماس با شما؟",
        options=(
            Option("morning", "۹ تا ۱۲"),
            Option("noon", "۱۲ تا ۱۶"),
            Option("evening", "۱۶ تا ۲۰"),
            Option("any", "فرقی نمی‌کند"),
        ),
        summary_label="ساعت مناسب تماس",
        show_if=lambda a: a.get("t_channel") in {"call", "whatsapp"},
    ),
    Step(
        id="t_notes",
        kind="text",
        section="اطلاعات تماس",
        title="نکتهٔ دیگری هست که بهتر است بدانیم؟",
        help="اختیاری است. اگر چیزی به ذهنتان نمی‌رسد، «رد کردن» را بزنید.",
        optional=True,
        placeholder="هر توضیحی که فکر می‌کنید کمک می‌کند",
        summary_label="توضیحات بیشتر",
    ),
)


STEPS_BY_ID: dict[str, Step] = {step.id: step for step in FLOW}


def visible_steps(answers: Answers) -> list[Step]:
    """The path this particular user actually walks, given their answers so far."""
    return [step for step in FLOW if step.visible(answers)]
