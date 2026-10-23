/* Validate the candidate index with the same decoder/contract used by the browser. */
const fs=require('node:fs');
const path=require('node:path');
global.crypto=require('node:crypto').webcrypto;
async function validate(root,candidate) {
    const {Loader,validateIndex}=require(path.join(root,'mayoristas-loader.js'));
    const index=validateIndex(JSON.parse(fs.readFileSync(candidate,'utf8')));
    const loader=new Loader(async url=>{
        const name=path.basename(url);
        const body=fs.readFileSync(name==='index.json'?candidate:path.join(path.dirname(candidate),name));
        return {ok:true,arrayBuffer:async()=>body.buffer.slice(body.byteOffset,body.byteOffset+body.byteLength)};
    });
    await loader.init();
    for(const f of index.fragments)await loader.shard(f);
    console.log('[VALIDATE] Mayoristas: index, hashes, schema, coverage and row counts verified');
}
validate(path.resolve(process.argv[2]),path.resolve(process.argv[3])).catch(error=>{console.error(error.message);process.exitCode=1;});
