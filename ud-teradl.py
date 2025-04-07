import os
import requests
import aiohttp
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from tqdm import tqdm

# Load environment variables
API_ID = int(os.getenv("API_ID", 22141398))
API_HASH = os.getenv("API_HASH", '0c8f8bd171e05e42d6f6e5a6f4305389')
BOT_TOKEN = os.getenv("BOT_TOKEN", '7277194738:AAHrewQsvKcPqeXYeMIbSk-nyUjgJ14kW8U')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

bot = Client("terabox_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_file_details(link):
    try:
        api_url = f"https://tera-dl.vercel.app/api?link={link}"
        logger.info(f"Fetching file details for: {link}")
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == "success":
                return data['Extracted Info']
        logger.error(f"Failed to fetch file details. Status code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching file details: {e}")
        return None

async def download_file_async(download_link, file_name, message):
    try:
        logger.info(f"Downloading file: {file_name}")
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        output_file = os.path.join(download_dir, file_name)

        async with aiohttp.ClientSession() as session:
            async with session.get(download_link) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('Content-Length', 0))
                    start_time = time.time()
                    downloaded = 0
                    with open(output_file, 'wb') as f:
                        with tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            unit_divisor=1024,
                            desc=file_name,
                            dynamic_ncols=True
                        ) as pbar:
                            while True:
                                chunk = await response.content.read(1024 * 64)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                elapsed_time = time.time() - start_time
                                speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                                pbar.set_postfix({
                                    "Speed": f"{speed / 1024:.2f} KB/s",
                                    "ETA": f"{(total_size - downloaded) / speed:.1f}s" if speed else "∞"
                                })
                                pbar.update(len(chunk))
                    logger.info(f"Downloaded successfully: {file_name}")
                    return output_file
                else:
                    logger.error(f"Download failed. Status: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

@bot.on_message(filters.regex(r"^(https?://)"))
async def handle_message(client, message):
    link = message.text.strip()
    logger.info(f"Received link: {link}")
    file_details = get_file_details(link)

    if file_details:
        for file_info in file_details:
            download_link = file_info.get("Direct Download Link")
            file_name = file_info.get("Title")
            size = file_info.get("Size")
            thumbnail = file_info['Thumbnails'].get("850x580")

            caption = f"**File Name:** {file_name}\n**Size:** {size}\n[Download Now]({download_link})"
            await message.reply_text(
                f"✅ **Link is valid!**\n\n"
                f"**Title:** {file_name}\n"
                f"**Size:** {size}\n"
                f"[Download Link]({download_link})",
            )

            if thumbnail:
                await message.reply_photo(thumbnail, caption=caption)
            else:
                await message.reply_text(caption)

            await message.reply_text("Do you want to proceed with the download? (Reply 'Yes' or 'No')")

            user_response = await bot.listen(message.chat.id)
            response_text = user_response.text.strip().lower()

            if response_text == "yes":
                file_path = await download_file_async(download_link, file_name, message)
                if file_path:
                    try:
                        await message.reply_document(file_path, caption=caption)
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
                        await message.reply("Error sending the file.")
                else:
                    await message.reply("Download failed.")
            elif response_text == "no":
                await message.reply("Download canceled.")
            else:
                await message.reply("Invalid response.")
    else:
        await message.reply("Failed to fetch file details. Please check the link.")


bot.run()

