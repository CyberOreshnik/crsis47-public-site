/* Optional reusable reader for generated public catalog pages.
 * Does not change the approved website until explicitly integrated.
 * Mount: createCollectionReader({collection:'books',root:'/collections/generated/',container,moreButton})
 */
export function createCollectionReader({collection,root,container,moreButton}){
 let index=null,page=0,controller=null;
 const safe=/^[a-z0-9-]+$/;
 if(!safe.test(collection))throw new Error('Invalid collection');
 async function loadNext(){
  controller?.abort();controller=new AbortController();
  if(!index){
   const response=await fetch(new URL('index.json',root),{signal:controller.signal});
   if(!response.ok)throw new Error('Catalog index unavailable');
   index=(await response.json())[collection];
   if(!index)throw new Error('Collection unavailable');
  }
  if(page>=index.pages.length)return;
  const file=index.pages[page];
  if(!/^[a-z0-9-]+\.json$/.test(file))throw new Error('Invalid page');
  const response=await fetch(new URL(file,root),{signal:controller.signal});
  if(!response.ok)throw new Error('Catalog page unavailable');
  const data=await response.json();
  if(data.collection!==collection||!Array.isArray(data.items)||data.items.length>index.page_size)throw new Error('Invalid page data');
  const fragment=document.createDocumentFragment();
  for(const item of data.items){
   const article=document.createElement('article');
   const title=document.createElement('h3');
   title.textContent=item.title;
   article.append(title);
   fragment.append(article);
  }
  container.append(fragment);
  page++;
  moreButton.hidden=page>=index.pages.length;
 }
 moreButton.addEventListener('click',()=>loadNext().catch(error=>{container.setAttribute('data-error','Catalog unavailable');console.error(error)}));
 return {loadNext,dispose(){controller?.abort()}};
}
