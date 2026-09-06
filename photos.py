"""Real photos for common dishes, platform-verified — the menu's middle fallback.

The owner's own pasted photo always wins. When there is none, stock_photo()
answers for dishes everyone recognises, and an unknown dish gets the neutral
tile from the template. Every URL here was verified live by the platform;
none was written by a model, and none should ever be edited by hand.
"""
import re

_PHOTOS = {
    "aloo tikki": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Aloo_Tikki_served_with_chutneys.jpg/330px-Aloo_Tikki_served_with_chutneys.jpg",
    "bhel puri": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Behael_Puri_%286105489342%29.jpg/330px-Behael_Puri_%286105489342%29.jpg",
    "biryani": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/%22Hyderabadi_Dum_Biryani%22.jpg/500px-%22Hyderabadi_Dum_Biryani%22.jpg",
    "burger": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/RedDot_Burger.jpg/330px-RedDot_Burger.jpg",
    "butter chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Butter_Chicken_%26_Butter_Naan_-_Home_-_Chandigarh_-_India_-_0006.jpg/500px-Butter_Chicken_%26_Butter_Naan_-_Home_-_Chandigarh_-_India_-_0006.jpg",
    "buttermilk": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Mint_lassi.jpg/500px-Mint_lassi.jpg",
    "cake": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Pound_layer_cake.jpg/330px-Pound_layer_cake.jpg",
    "chaas": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Mint_lassi.jpg/500px-Mint_lassi.jpg",
    "chaat": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Dahi_puri%2C_Doi_phuchka.jpg/330px-Dahi_puri%2C_Doi_phuchka.jpg",
    "chai": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Chai_In_Sakora.jpg/500px-Chai_In_Sakora.jpg",
    "chicken tikka": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/Tandoorimumbai.jpg/330px-Tandoorimumbai.jpg",
    "chole": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Chana_masala.jpg/500px-Chana_masala.jpg",
    "chole bhature": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Chole_Bhature_from_Nagpur.JPG/330px-Chole_Bhature_from_Nagpur.JPG",
    "chow mein": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg/500px-Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg",
    "coffee": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Filter_kaapi.JPG/330px-Filter_kaapi.JPG",
    "curd rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Curd_Rice.jpg/330px-Curd_Rice.jpg",
    "dal": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Punjabi_style_Dal_Makhani.jpg/500px-Punjabi_style_Dal_Makhani.jpg",
    "dal makhani": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Punjabi_style_Dal_Makhani.jpg/500px-Punjabi_style_Dal_Makhani.jpg",
    "dhokla": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Dhokla_on_Gujrart.jpg/330px-Dhokla_on_Gujrart.jpg",
    "dosa": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Dosa_at_Sri_Ganesha_Restauran%2C_Bangkok_%2844570742744%29.jpg/500px-Dosa_at_Sri_Ganesha_Restauran%2C_Bangkok_%2844570742744%29.jpg",
    "filter coffee": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Filter_kaapi.JPG/330px-Filter_kaapi.JPG",
    "french fries": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/French_Fries.JPG/330px-French_Fries.JPG",
    "fried rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Koh_Mak%2C_Thailand%2C_Fried_rice_with_seafood%2C_Thai_fried_rice.jpg/330px-Koh_Mak%2C_Thailand%2C_Fried_rice_with_seafood%2C_Thai_fried_rice.jpg",
    "fries": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/French_Fries.JPG/330px-French_Fries.JPG",
    "golgappa": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Pani_Puri1.JPG/330px-Pani_Puri1.JPG",
    "gulab jamun": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Gulab-jamun-wallpaper-1.jpg/330px-Gulab-jamun-wallpaper-1.jpg",
    "halwa": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Orient_sweets_%28special_halva%29_Samarkand%2C_Siyab.jpg/330px-Orient_sweets_%28special_halva%29_Samarkand%2C_Siyab.jpg",
    "ice cream": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg/330px-Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg",
    "idli": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Idli_Sambar.JPG/500px-Idli_Sambar.JPG",
    "jalebi": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Basavanagudi_Kadalekai_Parishe_%282025%29_Bangalore_%2886%29.jpg/500px-Basavanagudi_Kadalekai_Parishe_%282025%29_Bangalore_%2886%29.jpg",
    "kachori": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Rajasthani_Raj_Kachori.jpg/330px-Rajasthani_Raj_Kachori.jpg",
    "kathi roll": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Kolkata_Rolls.jpg/330px-Kolkata_Rolls.jpg",
    "kheer": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Kheer.jpg/500px-Kheer.jpg",
    "khichdi": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/63/Dall_Khichdi.jpg/330px-Dall_Khichdi.jpg",
    "korma": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Chicken_Korma.JPG/330px-Chicken_Korma.JPG",
    "lassi": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Salt_lassi.jpg/330px-Salt_lassi.jpg",
    "lemon rice": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Chitranna_and_Payasa.jpg/500px-Chitranna_and_Payasa.jpg",
    "malai kofta": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Koofteh_tabrizi.jpg/330px-Koofteh_tabrizi.jpg",
    "manchurian": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg/330px-Chicken_Manchurian_%28Hyderabad_Style%29_%2811960049916%29.jpg",
    "masala chai": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Chai_In_Sakora.jpg/500px-Chai_In_Sakora.jpg",
    "masala dosa": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Masala_Dosa_2023.jpg/500px-Masala_Dosa_2023.jpg",
    "milkshake": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Strawberry_milk_shake_%28cropped%29.jpg/330px-Strawberry_milk_shake_%28cropped%29.jpg",
    "momo": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Momo_nepal.jpg/330px-Momo_nepal.jpg",
    "momos": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Momo_nepal.jpg/330px-Momo_nepal.jpg",
    "naan": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Annapurna_Naan.jpg/330px-Annapurna_Naan.jpg",
    "noodles": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg/500px-Homemade_Chow_mein_with_shrimps_and_meat_with_a_choy_and_Choung.jpg",
    "omelette": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Gorgonzola_%2B_Bacon_Omelette_%40_Omelegg_%40_Amsterdam_%2816600947041%29.jpg/330px-Gorgonzola_%2B_Bacon_Omelette_%40_Omelegg_%40_Amsterdam_%2816600947041%29.jpg",
    "pakora": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Onion_pakora_-_a.jpg/330px-Onion_pakora_-_a.jpg",
    "paneer": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Panir_Paneer_Indian_cheese_fresh.jpg/330px-Panir_Paneer_Indian_cheese_fresh.jpg",
    "paneer butter masala": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Shahi_panner.jpg/330px-Shahi_panner.jpg",
    "paneer tikka": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Paneer_tikka.jpg/500px-Paneer_tikka.jpg",
    "pani puri": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Pani_Puri1.JPG/330px-Pani_Puri1.JPG",
    "papad": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Roasted_Papad_-_Howrah_2013-11-02_4068.jpg/330px-Roasted_Papad_-_Howrah_2013-11-02_4068.jpg",
    "paratha": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Triangle_paratha_%28cropped%29.JPG/500px-Triangle_paratha_%28cropped%29.JPG",
    "pasta": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/%28Pasta%29_by_David_Adam_Kess_%28pic.2%29.jpg/330px-%28Pasta%29_by_David_Adam_Kess_%28pic.2%29.jpg",
    "pastry": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/63/Making_puff_pastry_%28butter_and_Water_dough_%29_5.jpg/330px-Making_puff_pastry_%28butter_and_Water_dough_%29_5.jpg",
    "pav bhaji": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Bambayya_Pav_bhaji.jpg/330px-Bambayya_Pav_bhaji.jpg",
    "pizza": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Pizza-3007395.jpg/330px-Pizza-3007395.jpg",
    "poha": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Poha.jpg/500px-Poha.jpg",
    "pulao": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Afghan_Palo.jpg/330px-Afghan_Palo.jpg",
    "puri": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Fluffy_Poori_%28cropped%29.JPG/330px-Fluffy_Poori_%28cropped%29.JPG",
    "raita": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Cucumber-raita.jpg/330px-Cucumber-raita.jpg",
    "rajma": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Rajma_Masala_%2832081557778%29.jpg/330px-Rajma_Masala_%2832081557778%29.jpg",
    "rasgulla": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Rasgulla.jpg/500px-Rasgulla.jpg",
    "roll": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Kolkata_Rolls.jpg/330px-Kolkata_Rolls.jpg",
    "roti": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/2020-05-08_19_34_28_Chapati_being_made_in_a_pan_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg/500px-2020-05-08_19_34_28_Chapati_being_made_in_a_pan_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg",
    "sambar": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Pumpkin_sambar.JPG/500px-Pumpkin_sambar.JPG",
    "samosa": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg/500px-Samosas%2C_snack_food_at_Wikipedia%27s_16th_Birthday_celebration_in_Chittagong_%2801%29.jpg",
    "sandwich": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Bacon%2C_lettuce%2C_tomato%2C_and_avocado.jpg/330px-Bacon%2C_lettuce%2C_tomato%2C_and_avocado.jpg",
    "shawarma": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Shawarma_2.jpg/330px-Shawarma_2.jpg",
    "spring dosa": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Dosa_at_Sri_Ganesha_Restauran%2C_Bangkok_%2844570742744%29.jpg/330px-Dosa_at_Sri_Ganesha_Restauran%2C_Bangkok_%2844570742744%29.jpg",
    "spring roll": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Spring_Rolls_%283357696061%29.jpg/500px-Spring_Rolls_%283357696061%29.jpg",
    "tandoori chicken": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Chickentandoori.jpg/330px-Chickentandoori.jpg",
    "tea": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Chai_In_Sakora.jpg/500px-Chai_In_Sakora.jpg",
    "thali": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Vegetarian_Curry.jpeg/330px-Vegetarian_Curry.jpeg",
    "upma": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/A_photo_of_Upma.jpg/330px-A_photo_of_Upma.jpg",
    "uttapam": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Mini_Uttappam.jpg/500px-Mini_Uttappam.jpg",
    "vada": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Medu_Vada.JPG/500px-Medu_Vada.JPG",
    "vada pav": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Vada_Pav-Indian_street_food.JPG/500px-Vada_Pav-Indian_street_food.JPG",
    "veg kurma": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Chicken_Korma.JPG/330px-Chicken_Korma.JPG",
    # Ice-cream parlour set, verified 2026-08-25.
    "ice cream cone": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Strawberry_ice_cream_cone_%285076899310%29.jpg/330px-Strawberry_ice_cream_cone_%285076899310%29.jpg",
    "cone": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Strawberry_ice_cream_cone_%285076899310%29.jpg/330px-Strawberry_ice_cream_cone_%285076899310%29.jpg",
    "waffle cone": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Strawberry_ice_cream_cone_%285076899310%29.jpg/330px-Strawberry_ice_cream_cone_%285076899310%29.jpg",
    "strawberry ice cream": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Strawberry_ice_cream_cone_%285076899310%29.jpg/330px-Strawberry_ice_cream_cone_%285076899310%29.jpg",
    "strawberry scoop": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Strawberry_ice_cream_cone_%285076899310%29.jpg/330px-Strawberry_ice_cream_cone_%285076899310%29.jpg",
    "sundae": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/StrawberrySundae.jpg/330px-StrawberrySundae.jpg",
    "kulfi": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Matka_kulfi.jpg/330px-Matka_kulfi.jpg",
    "chocolate ice cream": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Ice_cream_cone_%28cropped%29.jpg/330px-Ice_cream_cone_%28cropped%29.jpg",
    "chocolate scoop": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Ice_cream_cone_%28cropped%29.jpg/330px-Ice_cream_cone_%28cropped%29.jpg",
    "vanilla ice cream": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg/330px-Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg",
    "vanilla scoop": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg/330px-Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg",
    "vanilla": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg/330px-Vanilla_Ice_Cream_Cone_at_Camp_Manitoulin.jpg",
    "softy": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Soft_Ice_cream.jpg/330px-Soft_Ice_cream.jpg",
    "soft serve": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Soft_Ice_cream.jpg/330px-Soft_Ice_cream.jpg",
    "banana split": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Banana_split_1.jpg/330px-Banana_split_1.jpg",
    "falooda": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Faluda.JPG/330px-Faluda.JPG",
    "faluda": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Faluda.JPG/330px-Faluda.JPG",
    "gelato": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Delicious_Gelato_on_display.jpg/330px-Delicious_Gelato_on_display.jpg",
    "ice cream sandwich": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/IceCreamSandwich.jpg/330px-IceCreamSandwich.jpg",
    "ice pop": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg/330px-Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg",
    "ice candy": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg/330px-Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg",
    "popsicle": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg/330px-Cucumber%2C_elderflower_and_mint_ice_pop_from_Nicepops_%2818159920902%29.jpg",
    "cassata": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Cassatasiciliana.jpg/330px-Cassatasiciliana.jpg",
    "pistachio": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Glace_%C3%A0_la_pistache-Lipari.jpg/330px-Glace_%C3%A0_la_pistache-Lipari.jpg",
    "pista": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Glace_%C3%A0_la_pistache-Lipari.jpg/330px-Glace_%C3%A0_la_pistache-Lipari.jpg",
    "brownie": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Chocolatebrownie.JPG/330px-Chocolatebrownie.JPG",
    "frozen yogurt": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/French_fry_frozen_yoghurt.jpg/330px-French_fry_frozen_yoghurt.jpg",
    "froyo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/French_fry_frozen_yoghurt.jpg/330px-French_fry_frozen_yoghurt.jpg",
    "ice cream cake": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Ice_Cream_swiss_roll.jpg/330px-Ice_Cream_swiss_roll.jpg",
    "mint chocolate chip": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/2020-04-27_18_23_07_A_spoonful_of_Friendly%27s_Mint_Chocolate_Chip_Ice_Cream_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg/330px-2020-04-27_18_23_07_A_spoonful_of_Friendly%27s_Mint_Chocolate_Chip_Ice_Cream_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg",
    "mint chip": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/2020-04-27_18_23_07_A_spoonful_of_Friendly%27s_Mint_Chocolate_Chip_Ice_Cream_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg/330px-2020-04-27_18_23_07_A_spoonful_of_Friendly%27s_Mint_Chocolate_Chip_Ice_Cream_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg",
    "cookies and cream": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Cookies_and_cream.JPG/330px-Cookies_and_cream.JPG",
    "oreo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Cookies_and_cream.JPG/330px-Cookies_and_cream.JPG",
    "neapolitan": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Neapolitan.jpg/330px-Neapolitan.jpg",
    "sorbet": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Strawberry_sorbet_zoomed.jpg/330px-Strawberry_sorbet_zoomed.jpg",
    "waffle": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Waffles_with_Strawberries.jpg/330px-Waffles_with_Strawberries.jpg",
    "rabri": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Homemade_Rabri.jpg/330px-Homemade_Rabri.jpg",
    "rabdi": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Homemade_Rabri.jpg/330px-Homemade_Rabri.jpg",
    "scoop": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg/330px-Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg",
    "family pack": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg/330px-Ice_cream_with_whipped_cream%2C_chocolate_syrup%2C_and_a_wafer_%28cropped%29.jpg",
}

# Longest keyword first, so "masala dosa" wins over "dosa", "spring roll"
# over "roll", and "paneer tikka" over "paneer".
_KEYWORDS = sorted(_PHOTOS, key=len, reverse=True)


def _normalize(name):
    """Lowercase, punctuation to spaces, padded — so keyword hits are whole
    words: 'Idli (2 pc)' matches 'idli', and 'price' can never match 'rice'."""
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).split()) + " "


def stock_photo(name):
    """A real, verified photo URL for a COMMON dish name, or None.

    None is an honest answer: the template then shows its neutral initial
    tile, which beats guessing — a wrong photo on a menu is worse than none.
    """
    n = _normalize(name)
    for key in _KEYWORDS:
        if " " + key + " " in n:
            return _PHOTOS[key]
    return None
