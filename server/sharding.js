export class GlobalDivider {
    static divide(base64Data, numBlocks) {
        if (numBlocks < 1) numBlocks = 1;

        const blockSize = Math.ceil(base64Data.length / numBlocks);
        const blocks = [];

        for (let i = 0; i < numBlocks; i++) {
            const start = i * blockSize;
            const end = start + blockSize;
            blocks.push(base64Data.substring(start, end));
        }

        return blocks;
    }
}
