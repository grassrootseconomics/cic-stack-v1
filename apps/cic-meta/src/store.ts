import { Syncable } from './sync';

interface Store {
	put(string, Syncable, boolean?)
	get(string):Syncable
	delete(string)
}

export { Store };
