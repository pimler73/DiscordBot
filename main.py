import discord

class Client(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}")
        
    async def on_message(self, message):
        if message.author == self.user:
            # So the bot doesn't reply to itself.
            return
        
        if "tomism" in message.content:
            await message.channel.send("Tell them to pound sand")
            # Only do one tomism.
            return
        
def main():
    intents = discord.Intents.default()
    intents.message_content = True

    client = Client(intents=intents)
    with open("secret.txt", "r") as file:
        api_key = file.readline()
    client.run(api_key)

if __name__ == "__main__":
    main()