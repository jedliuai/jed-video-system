import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// loadFont participates in Remotion's render delay; both Studio and export share it.
void loadFont({family: 'JedSans', url: staticFile('fonts/jed-sans-regular.ttf'), weight: '400'});
void loadFont({family: 'JedSans', url: staticFile('fonts/jed-sans-bold.ttf'), weight: '700'});
