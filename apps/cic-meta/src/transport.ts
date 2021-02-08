interface SubConsumer {
	post(string)
}

interface PubSub {
	pub(v:string):boolean
	close()
}

export { PubSub, SubConsumer };

