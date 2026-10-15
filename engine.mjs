import {readFile, writeFile} from 'node:fs/promises';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
const [engine, input, output] = process.argv.slice(2);
const source = await readFile(input,'utf8');
async function webcrackEngine(){
  const {webcrack} = await import('webcrack');
  const result = await webcrack(source, {jsx:true, unpack:true, deobfuscate:true});
  const modules=[];
  if(result.bundle?.modules){
    for(const [name, module] of Object.entries(result.bundle.modules)){
      modules.push({name,code:typeof module==='string'?module:module.code??''});
      if(modules.length>=200)break;
    }
  }
  return {engine:'webcrack', code:result.code, modules};
}
async function wakaruEngine(){
  // Use the installed Wakaru CLI rather than pretending its API is stable.
  // Configuration can override the command and arguments with RES_WAKARU_COMMAND.
  const command=process.env.RES_WAKARU_COMMAND || 'wakaru';
  const args=process.env.RES_WAKARU_ARGS ? JSON.parse(process.env.RES_WAKARU_ARGS) : ['--help'];
  return {engine:'wakaru', error:'Integração requer configuração explícita do CLI Wakaru (versões variam). Configure RES_WAKARU_COMMAND e RES_WAKARU_ARGS após verificar a sintaxe da versão instalada.'};
}
try {
 const result=engine==='webcrack'?await webcrackEngine():engine==='wakaru'?await wakaruEngine():{error:'Motor desconhecido'};
 await writeFile(output,JSON.stringify(result));
} catch(e) {await writeFile(output,JSON.stringify({engine,error:String(e.message||e)})); process.exitCode=1;}
